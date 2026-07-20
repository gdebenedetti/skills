from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

from quick_validate import validate_skill


class ValidateSkillTests(TestCase):
    def test_rejects_frontmatter_name_that_differs_from_directory(self):
        with TemporaryDirectory() as temporary_directory:
            skill_directory = Path(temporary_directory) / "correct-name"
            skill_directory.mkdir()
            (skill_directory / "SKILL.md").write_text(
                "---\n"
                "name: wrong-name\n"
                "description: Use this test skill when validating a catalog.\n"
                "---\n"
            )

            valid, message = validate_skill(str(skill_directory))

        self.assertFalse(valid)
        self.assertEqual(
            message,
            "Name 'wrong-name' must match directory 'correct-name'",
        )


if __name__ == "__main__":
    main()
