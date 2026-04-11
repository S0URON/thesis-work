"""QA Report models."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class TestStep(BaseModel):
    """Individual test step."""

    step_number: int
    action: str
    expected_result: Optional[str] = None


class TestScenario(BaseModel):
    """Detailed test scenario."""

    scenario_id: str = Field(description="Unique scenario identifier")
    title: str = Field(description="Test scenario title")
    objective: str = Field(description="What this test aims to verify")
    category: str = Field(description="Test category (e.g., Navigation, Forms, Localization)")
    priority: str = Field(description="Priority level: Critical, High, Medium, Low")
    preconditions: Optional[str] = Field(None, description="Required preconditions")
    test_steps: List[TestStep] = Field(default_factory=list)
    expected_results: List[str] = Field(default_factory=list)
    test_data: Optional[Dict[str, Any]] = Field(None, description="Required test data")
    automation_selector: Optional[str] = Field(
        None, description="CSS/XPath selector for automation"
    )
    notes: Optional[str] = Field(None, description="Additional notes")

    class Config:
        json_schema_extra = {
            "example": {
                "scenario_id": "NAV-001",
                "title": "Verify header navigation links",
                "objective": "Ensure all header links navigate correctly",
                "category": "Navigation",
                "priority": "High",
                "test_steps": [
                    {
                        "step_number": 1,
                        "action": "Click 'About' link",
                        "expected_result": "Navigate to /about",
                    }
                ],
            }
        }


class QAReport(BaseModel):
    """Complete QA analysis report."""

    website_url: HttpUrl = Field(description="Website URL analyzed")
    website_name: str = Field(description="Website name/title")
    analysis_date: datetime = Field(default_factory=datetime.now)
    languages_detected: List[str] = Field(default_factory=list)
    total_pages_analyzed: int = Field(0)
    critical_issues_found: int = Field(0)
    test_scenarios_generated: int = Field(0)

    # Content sections
    executive_summary: str = Field(description="Brief overview of findings")
    website_overview: str = Field(description="What the website does")
    site_structure: Dict[str, str] = Field(
        default_factory=dict, description="Map of pages and purposes"
    )
    test_scenarios: List[TestScenario] = Field(default_factory=list)
    potential_issues: List[str] = Field(default_factory=list)
    edge_cases: List[str] = Field(default_factory=list)
    test_data_requirements: Optional[Dict[str, Any]] = Field(None)
    automation_recommendations: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(None)

    class Config:
        json_schema_extra = {
            "example": {
                "website_url": "https://example.com",
                "website_name": "Example Corp",
                "languages_detected": ["English", "Arabic"],
                "total_pages_analyzed": 15,
                "test_scenarios_generated": 25,
            }
        }

    def to_markdown(self) -> str:
        """Convert report to markdown format."""
        md = f"""# QA Test Report: {self.website_name}

## 📋 Executive Summary
- **Website URL**: {self.website_url}
- **Analysis Date**: {self.analysis_date.strftime("%Y-%m-%d %H:%M:%S")}
- **Languages Detected**: {", ".join(self.languages_detected)}
- **Total Pages Analyzed**: {self.total_pages_analyzed}
- **Critical Issues Found**: {self.critical_issues_found}
- **Test Scenarios Generated**: {self.test_scenarios_generated}

## 🎯 Website Overview
{self.website_overview}

## 🗺️ Site Structure
"""
        for page, purpose in self.site_structure.items():
            md += f"- **{page}**: {purpose}\n"

        md += "\n## 🧪 Test Scenarios\n\n"

        # Group scenarios by category
        categories = {}
        for scenario in self.test_scenarios:
            if scenario.category not in categories:
                categories[scenario.category] = []
            categories[scenario.category].append(scenario)

        for category, scenarios in categories.items():
            md += f"\n### {category} Testing\n\n"
            for scenario in scenarios:
                md += f"**{scenario.scenario_id}: {scenario.title}**\n"
                md += f"- **Objective**: {scenario.objective}\n"
                md += f"- **Priority**: {scenario.priority}\n"
                if scenario.preconditions:
                    md += f"- **Preconditions**: {scenario.preconditions}\n"
                md += "- **Test Steps**:\n"
                for step in scenario.test_steps:
                    md += f"  {step.step_number}. {step.action}\n"
                    if step.expected_result:
                        md += f"     → {step.expected_result}\n"
                if scenario.automation_selector:
                    md += f"- **Automation Selector**: `{scenario.automation_selector}`\n"
                md += "\n"

        if self.potential_issues:
            md += "\n## 🚨 Potential Issues\n\n"
            for issue in self.potential_issues:
                md += f"- {issue}\n"

        if self.edge_cases:
            md += "\n## ⚠️ Edge Cases to Test\n\n"
            for edge_case in self.edge_cases:
                md += f"- {edge_case}\n"

        if self.automation_recommendations:
            md += "\n## 🔍 Automation Recommendations\n\n"
            for rec in self.automation_recommendations:
                md += f"- {rec}\n"

        if self.notes:
            md += f"\n## 📝 Additional Notes\n\n{self.notes}\n"

        return md
