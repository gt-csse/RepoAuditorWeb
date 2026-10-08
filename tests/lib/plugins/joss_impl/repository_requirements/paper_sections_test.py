import textwrap

from RepoAuditorWeb.lib.plugins.joss_impl.documents import Paper
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_sections import (
    PaperSectionsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


_SECTIONS = [
    "Summary",
    "Statement of need",
    "State of the field",
    "Software design",
    "Research impact statement",
    "AI usage disclosure",
]


# ----------------------------------------------------------------------
def test_Construct():
    requirement = PaperSectionsRequirement()

    assert requirement.name == "PaperSections"
    assert requirement.description == "Validates that the paper contains the sections that JOSS requires."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_AllPresent():
    text = "\n\n".join(f"# {section.upper()}\n\nText" for section in _SECTIONS)

    result = PaperSectionsRequirement().Evaluate(
        JOSSModule(),
        {"paper": Paper("paper/paper.md", text, {}, None)},
        {"skip": False, "sections": _SECTIONS},
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context == "`paper/paper.md` contains all of the required sections."
    assert result.rationale is not None


# ----------------------------------------------------------------------
def test_Missing():
    result = PaperSectionsRequirement().Evaluate(
        JOSSModule(),
        {"paper": Paper("paper/paper.md", "# Summary\n\n#  Statement   of need\n", {}, None)},
        {"skip": False, "sections": _SECTIONS},
    )

    assert result.result == EvaluateResultValue.Error
    assert (
        result.context
        == "`paper/paper.md` does not contain these sections: `State of the field`, `Software design`, `Research impact statement`, `AI usage disclosure`."
    )
    assert result.resolution == textwrap.dedent(
        """\
        Add a heading for each missing section to `paper/paper.md` (for example, `# State of the field`).
        See [What should my paper contain?](https://joss.readthedocs.io/en/latest/paper.html#what-should-my-paper-contain)
        for a description of each section.
        """,
    )
