"""
Tests for traceability module.
"""

import pytest
from src.traceability import (
    TraceabilityLogger,
    MatchTrace,
    ScoreTrace,
    AnalysisTrace,
    trace_logger,
)


class TestTraceabilityLogger:
    """Test cases for TraceabilityLogger."""
    
    def test_start_analysis_creates_trace(self):
        """Test that start_analysis creates a valid trace."""
        logger = TraceabilityLogger()
        trace = logger.start_analysis("test input", "git_diff")
        
        assert trace is not None
        assert trace.input_type == "git_diff"
        assert trace.input_hash is not None
        assert len(trace.input_hash) == 12  # MD5 hash truncated to 12 chars
    
    def test_log_rule_evaluation_increments_counter(self):
        """Test that logging rule evaluation increments total count."""
        logger = TraceabilityLogger()
        logger.start_analysis("test", "generic")
        
        logger.log_rule_evaluation(
            rule_id="rule-1",
            rule_name="Test Rule",
            matched=True,
            matched_keywords=["keyword"],
        )
        
        assert logger.current_trace.total_rules_evaluated == 1
        assert "rule-1" in logger.current_trace.rules_matched
    
    def test_log_rule_evaluation_unmatched(self):
        """Test logging unmatched rule."""
        logger = TraceabilityLogger()
        logger.start_analysis("test", "generic")
        
        logger.log_rule_evaluation(
            rule_id="rule-1",
            rule_name="Test Rule",
            matched=False,
        )
        
        assert logger.current_trace.total_rules_evaluated == 1
        assert len(logger.current_trace.rules_matched) == 0
    
    def test_log_score_calculation(self):
        """Test logging score calculation."""
        logger = TraceabilityLogger()
        logger.start_analysis("test", "generic")
        
        # Must log a rule match first before logging score
        logger.log_rule_evaluation(
            rule_id="rule-1",
            rule_name="Test Rule",
            matched=True,
            matched_keywords=["keyword"],
        )
        
        dimensions = {"business_impact": 3, "data_consistency": 2}
        logger.log_score_calculation(
            dimensions=dimensions,
            raw_score=5,
            final_score=5,
        )
        
        assert logger.current_trace.score_trace is not None
        assert logger.current_trace.score_trace.raw_score == 5
        assert logger.current_trace.score_trace.dimension_breakdown == dimensions
    
    def test_log_score_with_adjustment(self):
        """Test logging score with adjustment."""
        logger = TraceabilityLogger()
        logger.start_analysis("test", "generic")
        
        # Must log a rule match first before logging score
        logger.log_rule_evaluation(
            rule_id="rule-1",
            rule_name="Test Rule",
            matched=True,
            matched_keywords=["keyword"],
        )
        
        logger.log_score_calculation(
            dimensions={"business_impact": 3},
            raw_score=10,
            final_score=9,
            adjustment_reason="Downgraded due to negative keywords",
        )
        
        st = logger.current_trace.score_trace
        assert st.level_before_adjustment == "high"
        assert st.level_after_adjustment == "medium"
        assert st.adjustment_reason is not None
    
    def test_finalize_trace(self):
        """Test finalizing trace with execution time."""
        logger = TraceabilityLogger()
        logger.start_analysis("test", "generic")
        
        trace = logger.finalize(execution_time_ms=150.5)
        
        assert trace.execution_time_ms == 150.5
        assert trace.timestamp is not None
    
    def test_export_json(self):
        """Test exporting trace to JSON."""
        logger = TraceabilityLogger()
        logger.start_analysis("test input content", "api_change")
        
        logger.log_rule_evaluation(
            rule_id="rule-1",
            rule_name="Payment Rule",
            matched=True,
            matched_keywords=["payment", "transaction"],
        )
        
        logger.finalize(100.0)
        
        json_output = logger.export_trace(format="json")
        
        assert '"input_hash"' in json_output
        assert '"input_type": "api_change"' in json_output
        assert '"rules_matched"' in json_output
        assert '"payment"' in json_output
    
    def test_export_markdown(self):
        """Test exporting trace to Markdown."""
        logger = TraceabilityLogger()
        logger.start_analysis("test", "git_diff")
        
        logger.log_rule_evaluation(
            rule_id="rule-1",
            rule_name="Test Rule",
            matched=True,
            matched_keywords=["keyword"],
        )
        
        logger.finalize(50.0)
        
        md_output = logger.export_trace(format="markdown")
        
        assert "# Traceability Report" in md_output
        assert "**Input Hash:**" in md_output
        assert "## Rules Evaluation" in md_output
        assert "rule-1" in md_output
    
    def test_multiple_rules_match(self):
        """Test logging multiple rule matches."""
        logger = TraceabilityLogger()
        logger.start_analysis("test", "generic")
        
        for i in range(3):
            logger.log_rule_evaluation(
                rule_id=f"rule-{i}",
                rule_name=f"Rule {i}",
                matched=True,
                matched_keywords=[f"kw{i}"],
            )
        
        assert logger.current_trace.total_rules_evaluated == 3
        assert len(logger.current_trace.rules_matched) == 3
        assert len(logger.current_trace.match_traces) == 3
    
    def test_empty_trace_export(self):
        """Test exporting empty trace."""
        logger = TraceabilityLogger()
        result = logger.export_trace(format="json")
        assert result == ""


class TestScoreToLevelConversion:
    """Test score to level conversion logic."""
    
    def test_low_score(self):
        assert TraceabilityLogger._score_to_level(0) == "low"
        assert TraceabilityLogger._score_to_level(4) == "low"
    
    def test_medium_score(self):
        assert TraceabilityLogger._score_to_level(5) == "medium"
        assert TraceabilityLogger._score_to_level(9) == "medium"
    
    def test_high_score(self):
        assert TraceabilityLogger._score_to_level(10) == "high"
        assert TraceabilityLogger._score_to_level(15) == "high"


class TestGlobalTraceLogger:
    """Test the global trace_logger instance."""
    
    def test_global_instance_exists(self):
        """Test that global trace_logger is available."""
        assert trace_logger is not None
        assert isinstance(trace_logger, TraceabilityLogger)
    
    def test_global_instance_reusable(self):
        """Test that global instance can be reused across analyses."""
        trace_logger.start_analysis("input1", "type1")
        trace_logger.finalize(10.0)
        
        trace_logger.start_analysis("input2", "type2")
        trace = trace_logger.finalize(20.0)
        
        assert trace.input_type == "type2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])