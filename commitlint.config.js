module.exports = {
    extends: ["@commitlint/config-conventional"],
    ignores: [(msg) => /Signed-off-by: dependabot\[bot]/m.test(msg)],
    rules: {
        'type-enum': [
			2,
			'always',
			[
				'chore',
				'docs',
				'feat',
				'fix',
				'major'
			],
        ]
    }
};
