from student_api import rag_embedding_shift, rag_length_shift


def test_rag_length_collapse_is_detected():
    baseline_batch_means = [40, 42, 39, 41, 43, 40, 42]
    current_texts = ["x y", "a b c", "one two"]
    assert rag_length_shift(current_texts, baseline_batch_means)["is_anomaly"] is True


def test_rag_embedding_norm_drift():
    baseline_norms = [1.0, 1.02, 0.99, 1.01, 1.0]
    drifted_norms = [2.5, 2.6, 2.7, 2.55]
    result = rag_embedding_shift(drifted_norms, baseline_norms)
    assert result["is_anomaly"] is True

