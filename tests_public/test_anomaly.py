from student_api import detect_metric


def test_large_volume_drop_is_anomaly():
    history = [1000, 1010, 995, 1008, 1004, 1012, 998]
    result = detect_metric(300, history, method="zscore")
    assert result["is_anomaly"] is True


def test_stable_value_is_not_anomaly():
    history = [1000, 1010, 995, 1008, 1004, 1012, 998]
    result = detect_metric(1002, history, method="zscore")
    assert result["is_anomaly"] is False


def test_mad_detector_handles_outliers_and_zero_mad():
    history_identical = [500, 500, 500, 500, 500]
    result_same = detect_metric(500, history_identical, method="mad")
    assert result_same["is_anomaly"] is False

    result_diff = detect_metric(100, history_identical, method="mad")
    assert result_diff["is_anomaly"] is True


def test_auto_detector_uses_context_segmentation():
    history_all = [100, 105, 500, 510, 102, 520, 104]
    same_dow_history = [100, 105, 102, 104, 101]
    # Current value 103 is normal for this weekday (segment), but would look anomalous against overall mean if unsegmented
    result = detect_metric(
        103,
        history_all,
        method="auto",
        context={"day_of_week": 5, "same_segment_history": same_dow_history},
    )
    assert result["is_anomaly"] is False

