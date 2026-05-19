"""
Traceability module for Quality Gate Agent.

Provides end-to-end traceability for risk scoring decisions,
ensuring every output can be traced back to:
- source code location (file, line)
- matched rule ID and version
- specific keyword matches
- calculation steps
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class MatchTrace:
    """Trace for a single rule match."""
    rule_id: str
    rule_name: str
    rule_version: str = "1.0"
    source_file: str = ""
    line_numbers: List[int] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    keyword_locations: Dict[str, List[int]] = field(default_factory=dict)
    negative_keywords_matched: List[str] = field(default_factory=list)
    calculation_steps: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ScoreTrace:
    """Trace for risk score calculation."""
    raw_score: int
    final_score: int
    level_before_adjustment: str
    level_after_adjustment: str
    adjustment_reason: Optional[str] = None
    calculation_formula: str = ""
    dimension_breakdown: Dict[str, int] = field(default_factory=dict)


@dataclass
class AnalysisTrace:
    """Complete trace for an analysis run."""
    input_hash: str = ""
    input_type: str = ""  # "git_diff", "api_change", "openapi"
    ruleset_version: str = ""
    total_rules_evaluated: int = 0
    rules_matched: List[str] = field(default_factory=list)
    match_traces: List[MatchTrace] = field(default_factory=list)
    score_trace: Optional[ScoreTrace] = None
    execution_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class TraceabilityLogger:
    """Logger for capturing traceability information."""
    
    def __init__(self):
        self.current_trace: Optional[AnalysisTrace] = None
    
    def start_analysis(self, input_text: str, input_type: str, ruleset_version: str = "1.0") -> AnalysisTrace:
        """Start a new analysis trace."""
        import hashlib
        input_hash = hashlib.md5(input_text.encode()).hexdigest()[:12]
        
        self.current_trace = AnalysisTrace(
            input_hash=input_hash,
            input_type=input_type,
            ruleset_version=ruleset_version,
        )
        return self.current_trace
    
    def log_rule_evaluation(
        self,
        rule_id: str,
        rule_name: str,
        matched: bool,
        matched_keywords: List[str] = None,
        negative_keywords: List[str] = None,
        keyword_locations: Dict[str, List[int]] = None,
    ) -> None:
        """Log a rule evaluation event."""
        if not self.current_trace:
            return
            
        self.current_trace.total_rules_evaluated += 1
        
        if matched:
            self.current_trace.rules_matched.append(rule_id)
            
            match_trace = MatchTrace(
                rule_id=rule_id,
                rule_name=rule_name,
                line_numbers=sorted(
                    {
                        line_number
                        for line_numbers in (keyword_locations or {}).values()
                        for line_number in line_numbers
                    }
                ),
                matched_keywords=matched_keywords or [],
                negative_keywords_matched=negative_keywords or [],
                keyword_locations=keyword_locations or {},
            )
            self.current_trace.match_traces.append(match_trace)
    
    def log_score_calculation(
        self,
        dimensions: Dict[str, int],
        raw_score: int,
        final_score: int,
        adjustment_reason: Optional[str] = None,
    ) -> None:
        """Log score calculation steps for the most recent match."""
        if not self.current_trace or not self.current_trace.match_traces:
            return
        
        # Attach score trace to the most recent match
        level_before = self._score_to_level(raw_score)
        level_after = self._score_to_level(final_score)
        
        score_trace = ScoreTrace(
            raw_score=raw_score,
            final_score=final_score,
            level_before_adjustment=level_before,
            level_after_adjustment=level_after,
            adjustment_reason=adjustment_reason,
            dimension_breakdown=dimensions.copy(),
            calculation_formula=f"sum({dimensions}) = {raw_score}",
        )
        
        # Store in the most recent match trace
        self.current_trace.match_traces[-1].calculation_steps.append({
            "raw_score": raw_score,
            "final_score": final_score,
            "adjustment_reason": adjustment_reason,
            "dimension_breakdown": dimensions.copy(),
        })
        
        # Also store at analysis level for the overall score (last one wins, but that's OK for now)
        self.current_trace.score_trace = score_trace
    
    def finalize(self, execution_time_ms: float) -> AnalysisTrace:
        """Finalize the trace and return it."""
        if self.current_trace:
            self.current_trace.execution_time_ms = execution_time_ms
        return self.current_trace
    
    def export_trace(self, format: str = "json") -> str:
        """Export trace in specified format."""
        if not self.current_trace:
            return ""
        
        if format == "json":
            return self._to_json()
        elif format == "markdown":
            return self._to_markdown()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _to_json(self) -> str:
        """Convert trace to JSON."""
        trace_dict = {
            "input_hash": self.current_trace.input_hash,
            "input_type": self.current_trace.input_type,
            "ruleset_version": self.current_trace.ruleset_version,
            "total_rules_evaluated": self.current_trace.total_rules_evaluated,
            "rules_matched": self.current_trace.rules_matched,
            "execution_time_ms": self.current_trace.execution_time_ms,
            "timestamp": self.current_trace.timestamp,
            "matches": [
                {
                    "rule_id": mt.rule_id,
                    "rule_name": mt.rule_name,
                    "matched_keywords": mt.matched_keywords,
                    "negative_keywords": mt.negative_keywords_matched,
                    "line_numbers": mt.line_numbers,
                    "keyword_locations": mt.keyword_locations,
                }
                for mt in self.current_trace.match_traces
            ],
        }
        
        if self.current_trace.score_trace:
            trace_dict["score_calculation"] = {
                "raw_score": self.current_trace.score_trace.raw_score,
                "final_score": self.current_trace.score_trace.final_score,
                "adjustment_reason": self.current_trace.score_trace.adjustment_reason,
                "dimension_breakdown": self.current_trace.score_trace.dimension_breakdown,
            }
        
        return json.dumps(trace_dict, indent=2)
    
    def _to_markdown(self) -> str:
        """Convert trace to Markdown report."""
        lines = [
            "# Traceability Report",
            "",
            f"**Input Hash:** `{self.current_trace.input_hash}`",
            f"**Input Type:** {self.current_trace.input_type}",
            f"**Ruleset Version:** {self.current_trace.ruleset_version}",
            f"**Analysis Time:** {self.current_trace.execution_time_ms:.2f}ms",
            f"**Timestamp:** {self.current_trace.timestamp}",
            "",
            "## Rules Evaluation",
            "",
            f"- Total rules evaluated: {self.current_trace.total_rules_evaluated}",
            f"- Rules matched: {len(self.current_trace.rules_matched)}",
            "",
            "### Matched Rules",
            "",
        ]
        
        for mt in self.current_trace.match_traces:
            lines.extend([
                f"#### {mt.rule_id}: {mt.rule_name}",
                "",
                f"- **Matched Keywords:** {', '.join(mt.matched_keywords)}",
                f"- **Negative Keywords:** {', '.join(mt.negative_keywords_matched) or 'None'}",
                f"- **Input Lines:** {', '.join(str(line) for line in mt.line_numbers) or 'N/A'}",
                "",
            ])
            if mt.keyword_locations:
                lines.extend([
                    "| Keyword | Lines |",
                    "|---------|-------|",
                ])
                for keyword, line_numbers in mt.keyword_locations.items():
                    lines.append(f"| {keyword} | {', '.join(str(line) for line in line_numbers)} |")
                lines.append("")
        
        if self.current_trace.score_trace:
            st = self.current_trace.score_trace
            lines.extend([
                "## Score Calculation",
                "",
                f"- **Raw Score:** {st.raw_score}",
                f"- **Final Score:** {st.final_score}",
                f"- **Level Change:** {st.level_before_adjustment} → {st.level_after_adjustment}",
                "",
                "### Dimension Breakdown",
                "",
                "| Dimension | Score |",
                "|-----------|-------|",
            ])
            for dim, score in st.dimension_breakdown.items():
                lines.append(f"| {dim} | {score} |")
            
            if st.adjustment_reason:
                lines.extend([
                    "",
                    f"**Adjustment:** {st.adjustment_reason}",
                ])
        
        return '\n'.join(lines)
    
    @staticmethod
    def _score_to_level(score: int) -> str:
        """Convert score to risk level."""
        if score >= 10:
            return "high"
        elif score >= 5:
            return "medium"
        return "low"


# Global logger instance
trace_logger = TraceabilityLogger()
