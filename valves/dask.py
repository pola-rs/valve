def sessionize(dataf, user_col="user", ts_col="timestamp", threshold=20 * 60):
    """
    Adds a session to the dataset.

    This function is meant to be used in a `.pipe()`-line.

    Arguments:
        - dataf: dask dataframe
        - user_col: name of the column containing the user id
        - ts_col: name of the column containing the timestamp
        - threshold: time in seconds to consider a user inactive
    """
    return (
        dataf.sort_values([user_col, ts_col])
        .assign(
            ts_diff=lambda d: (d[ts_col] - d[ts_col].shift()).dt.seconds > threshold,
            char_diff=lambda d: (d[user_col].diff() != 0),
            new_session_mark=lambda d: d["ts_diff"] | d["char_diff"],
            session=lambda d: d["new_session_mark"].fillna(0).cumsum(),
        )
        .drop(columns=["char_diff", "ts_diff", "new_session_mark"])
    )


def bayes_average(
    dataf, group_cols, target_col, C, prior_mean=None, out_col="bayes_avg"
):
    r"""
    Computes the Bayes average for a target column.

    The average is calculated per formula found on [wikipedia](https://en.wikipedia.org/wiki/Bayesian_average).

    $$
    \bar{x}=\frac{C m+\sum_{i=1}^{n} x_{i}}{C+n}
    $$

    This function is meant to be used in a `.pipe()`-line.

    Arguments:
        - dataf: dask dataframe
        - group_cols: list of columns to group by
        - target_col: name of the column containing the target value, typically a rating
        - C: smoothing parameter
        - prior_mean: optional, a prior mean to use instead of the mean of the target column
        - out_col: name of the column to output
    """
    if prior_mean is None:
        prior_mean = dataf[target_col].mean()
    to_join_back = (
        dataf.groupby(group_cols)[target_col]
        .agg(["sum", "size"])
        .assign(**{out_col: lambda d: (C * prior_mean + d["sum"]) / (C + d["size"])})
        .drop(columns=["sum", "size"])
    )
    return dataf.join(to_join_back, on=group_cols).reset_index()
