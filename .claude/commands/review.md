# PR File Investigation

Conduct a systematic file-by-file PR review using GitHub CLI and codebase analysis.

## Instructions

1. **Fetch PR Details**
   - Use `gh pr view $ARGUMENTS --json files,title,body` to get PR information
   - If no PR number provided, ask user to specify PR number

2. **Initial Setup**
   - Read the PR description and understand the scope of changes
   - Identify all modified files in the PR
   - Prepare for systematic file-by-file review

3. **File Analysis Process**
   For the specified file (or first file if none specified):
   - Examine the file contents and changes
   - Cross-reference against PR_CHECKLIST requirements
   - Analyze implementation approach and patterns

4. **Evidence Gathering**
   - Search the codebase for similar implementations
   - Find supporting or conflicting patterns in related files
   - Identify any inconsistencies with existing conventions
   - Check for proper imports, types, and dependencies

5. **Provide Structured Report**
   - **File Overview**: Brief description of changes
   - **PR_CHECKLIST Compliance**: Check each point with evidence (PR_CHECKLIST.MD)
   - **Codebase Analysis**: Supporting/refuting evidence from other files
   - **Recommendations**: Specific improvements or approvals
   - **Next Steps**: Ready for next file review

6. **Wait for User Approval**
   - Present findings clearly
   - Wait for user review before proceeding to next file
   - Ask for specific file if user wants to jump to different file

## Usage Examples
- `/investigate 1550` - Review PR 1550 starting with first file
- `/investigate 1550 src/components/Header.tsx` - Review specific file in PR 1550
