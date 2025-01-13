module.exports = {
    extends: ["@commitlint/config-conventional"],
    ignores: [(msg) => /Signed-off-by: dependabot\[bot]/m.test(msg)],
    rules: {
        // Disable the rule that enforces lowercase in subject
        "subject-case": [0], // 0 = disable, 1 = warn, 2 = error
    },

};
