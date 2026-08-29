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


def test_known_event_suppresses_anomaly():
    history = [100, 102, 101, 99, 103, 98, 100]
    result = detect_metric(
        500,
        history,
        method="auto",
        context={"known_event": "flash_sale", "metric_name": "row_count"},
    )
    assert result["is_anomaly"] is False
    assert "suppressed_by_known_event" in result["reason"]


def test_quantized_zero_mad_practical_scale():
    history_quantized = [100, 100, 100, 100, 100, 100, 100]
    # 1% minor variation should not alert
    res_minor = detect_metric(101, history_quantized, method="mad")
    assert res_minor["is_anomaly"] is False

    # Major drop should alert
    res_collapse = detect_metric(30, history_quantized, method="mad")
    assert res_collapse["is_anomaly"] is True


def test_nonfinite_inputs_handled():
    res_nan = detect_metric(float("nan"), [100, 102, 101, 99, 100], method="mad")
    assert res_nan["is_anomaly"] is True

    res_inf = detect_metric(float("inf"), [100, 102, 101, 99, 100], method="zscore")
    assert res_inf["is_anomaly"] is True



