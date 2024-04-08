module.exports = {
    extends: ["@commitlint/config-conventional"],
    ignores: [(msg) => /Signed-off-by: dependabot\[bot]/m.test(msg)],
};
