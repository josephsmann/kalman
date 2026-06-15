def test_public_exports():
    import solveit_widget as sw

    assert hasattr(sw, "SolveItWidget")
    assert hasattr(sw, "LLMClient")
    assert hasattr(sw, "ClaudeClient")
    assert hasattr(sw, "FakeClient")
