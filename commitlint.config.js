import {
	RuleConfigSeverity,
} from '@commitlint/types';

module.exports = {
    extends: ["@commitlint/config-conventional"],
    ignores: [(msg) => /Signed-off-by: dependabot\[bot]/m.test(msg)],
    rules: {
        'type-enum': [
			RuleConfigSeverity.Error,
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
