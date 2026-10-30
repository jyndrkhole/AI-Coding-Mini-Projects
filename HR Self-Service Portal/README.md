# Project: HR Self-Service Portal

## 1. Your Role

Act as a senior full-stack software architect, product designer, UI/UX specialist, and security engineer.

Design and develop a production-minded, modern HR Self-Service Portal for a small organization that does not have a dedicated HR department.

The application will initially focus on employee leave management. It should be simple for employees to use and efficient for administrators to maintain.

Build a real, functional, database-backed application—not just a visual prototype.

Take ownership of the complete implementation, including frontend, backend, database schema, authentication, authorization, validation, error handling, testing, and documentation.

## 2. Product Vision

Create a polished, intuitive HR portal that centralizes employee leave management.

The portal should have two active roles in the initial release:

1. Employee
2. Administrator

A third role, Manager, will be introduced in a later phase.

The architecture must support future enhancements without requiring a major redesign.

### Initial release features

- Secure employee login.
- Employee dashboard.
- Employee profile.
- Leave application and submission.
- Leave history.
- Leave balance tracking.
- Leave calendar.
- Leave cancellation.
- Administrator dashboard.
- Employee management.
- Leave management across all employees.
- Configurable leave types and policies.
- Leave balance adjustments with audit history.
- Basic reports and analytics.
- Responsive design for desktop, tablet, and mobile.

### Future enhancements

Keep the architecture ready for:

- Manager-based leave approval workflows.
- Manager-specific permissions.
- Email notifications.
- Public holiday management.
- Automated leave accrual.
- Employee onboarding and offboarding.
- Attendance management.
- Employee document management.
- Company announcements.
- Payroll-related integrations.

Do not build all future features now. Focus on delivering a complete, reliable leave management system first.

---

## 3. UI/UX Design Requirements

The visual quality of this application is a major priority.

The portal should look like a premium, modern SaaS product, with the simplicity of Linear, the clarity of Notion, and the professionalism of a well-designed enterprise dashboard.

Use these products as inspiration for visual quality and interaction patterns only. Do not copy their interfaces.

### Design principles

- Clean, modern, professional, and welcoming.
- Minimal visual clutter.
- Clear information hierarchy.
- Generous whitespace.
- Consistent spacing and typography.
- Attractive cards with subtle borders.
- Rounded corners used consistently.
- Subtle shadows only where appropriate.
- Smooth, restrained animations.
- Clear loading, success, empty, and error states.
- Accessible contrast and keyboard navigation.
- Responsive layouts.
- Consistent design across employee and administrator screens.

The application should feel pleasant to use every day.

### Standard color palette

Use a professional, neutral color system.

Primary:
- Indigo: #4F46E5
- Dark indigo: #3730A3

Secondary:
- Slate: #64748B

Background:
- Main background: #F8FAFC
- Card background: #FFFFFF

Text:
- Primary text: #0F172A
- Secondary text: #64748B

Borders:
- #E2E8F0

Semantic colors:
- Success: #16A34A
- Warning: #D97706
- Error: #DC2626
- Informational: #0284C7

Use semantic colors consistently.

Do not use excessive gradients, bright neon colors, decorative backgrounds, or unnecessary animations.

The application should be predominantly white and light neutral colors, with indigo as its primary brand color.

Status colors should always be accompanied by readable text or an icon.

### Typography

Use Inter or another suitable modern sans-serif font.

Use consistent typography for:
- Page titles.
- Section headings.
- Body text.
- Labels.
- Form fields.
- Buttons.
- Tables.
- Dashboard metrics.

### Layout

Create a modern dashboard layout with:

1. A persistent left sidebar on desktop.
2. A compact top navigation bar.
3. A main content area.
4. A user profile menu.
5. Notifications or a notification placeholder for future use.

The sidebar should be collapsible.

On mobile, replace the desktop sidebar with a suitable drawer or compact navigation.

Include:
- Company logo placeholder.
- Application name: PeopleHub.
- Employee or administrator profile.
- Role-appropriate navigation.
- Logout option.

Use a configurable company name and logo rather than hardcoding organization-specific branding throughout the application.

### Reusable UI components

Create reusable components for:

- Buttons.
- Input fields.
- Select fields.
- Date pickers.
- Dialogs and confirmation modals.
- Status badges.
- Metric cards.
- Data tables.
- Search and filters.
- Pagination.
- Toast notifications.
- Empty states.
- Loading skeletons.
- Error states.
- Calendar events.
- User avatars or initials.

Maintain consistent behavior and styling across all screens.

---

## 4. User Roles and Permissions

Implement role-based access control on the server.

Hiding a button or navigation item is not sufficient authorization.

### Employee role

Employees should be able to:

- Log in securely.
- View their own dashboard.
- View their own profile.
- View their leave balances.
- Apply for leave.
- View their leave history.
- View leave request details.
- Cancel eligible leave requests.
- View the company leave calendar.
- Filter the calendar by date and leave type.
- View their own leave requests and statuses.
- View relevant company holidays when configured.

Employees must not be able to:

- View private employee information belonging to other employees.
- Modify another employee's leave requests.
- Modify their own leave balance directly.
- Assign themselves an administrator role.
- Approve their own leave requests.
- Access administrator APIs or data.

The team calendar should expose only the information necessary for planning, such as employee name, dates, and leave status. Do not expose private leave reasons or other sensitive details to ordinary employees.

### Administrator role

Administrators should be able to:

- View the organization-wide dashboard.
- View all employee records.
- Create employee records.
- Edit employee details.
- Activate or deactivate employees.
- Assign appropriate roles.
- Configure leave types.
- Configure leave policies.
- Configure the leave year.
- View and manage leave requests across employees.
- View all employees' leave balances.
- Make authorized leave balance adjustments.
- Cancel or modify leave requests when operationally necessary.
- View the organization-wide leave calendar.
- Filter and search employees.
- Generate leave reports.
- View the audit trail.

Administrative changes to balances, employee roles, and leave requests must be validated and recorded in the audit log.

Do not allow an administrator to access authentication secrets or passwords.

### Future Manager role

Prepare the data model and authorization design for a future Manager role.

In the later phase, managers should be able to:

- View their assigned team.
- View team leave calendars.
- Approve or reject leave requests.
- Provide comments when rejecting requests.
- Review requests awaiting their action.

The future manager approval workflow must be implemented as a separate enhancement.

For the initial release, employee leave requests should follow the configured submission workflow and be manageable by administrators.

Do not simulate manager approvals before the feature is implemented.

---

## 5. Authentication and Account Management

Implement secure authentication.

Requirements:

- Login using email and password, or a suitable organization-approved authentication provider.
- Secure password hashing if password-based authentication is used.
- Server-side session management.
- Protected application routes.
- Server-side role verification.
- Logout functionality.
- Appropriate session expiration.
- Login error handling.
- Password reset support or a documented administrative reset process.
- Protection against common authentication attacks.

Never store plaintext passwords.

Do not provide a publicly accessible registration page that allows anyone to create an employee or administrator account.

Employee accounts must be created or provisioned through an authorized process.

Do not hardcode production credentials.

If an initial administrator account is required for development, provide a secure setup procedure that does not expose credentials in source control.

---

## 6. Employee Dashboard

Create a visually attractive employee dashboard.

The dashboard should answer four questions immediately:

1. How much leave do I have?
2. What leave have I applied for?
3. What leave is coming up?
4. What do I need to do next?

### Welcome section

Display:

- A personalized greeting.
- Employee name.
- Current date.
- A prominent "Apply for Leave" button.

### Leave balance cards

Display the employee's balance for each configured leave type.

Each card should show:

- Leave type.
- Available balance.
- Total allocated entitlement.
- Used leave.
- Pending leave, separately identified.
- A subtle visual indicator of usage where useful.

Do not count pending requests as approved leave.

Clearly distinguish:
- Available balance.
- Approved leave already consumed.
- Approved future leave.
- Pending requests.

The exact balance calculation must follow the configured policy.

### Upcoming leave

Show a compact list of upcoming approved leave requests.

Include:
- Start date.
- End date.
- Leave type.
- Number of leave days.
- Status.

### Recent requests

Display recent leave requests with statuses such as:

- Pending.
- Approved.
- Rejected.
- Cancelled.

In the initial workflow, use only the statuses applicable to the actual implemented process.

### Quick actions

Provide clear actions for:

- Apply for leave.
- View leave calendar.
- View leave history.

### Empty state

If the employee has not submitted any leave requests, display a friendly empty state with a call to action.

Never display fabricated leave balances or fake requests in production.

---

## 7. Leave Application

Create a clean, intuitive leave application form.

### Required fields

- Leave type.
- Start date.
- End date.
- Reason or comments, if required by the configured policy.

Optional:
- Half-day selection, if supported by the leave policy.

Automatically calculate the requested number of leave days.

### Date calculation

The calculation must respect configurable rules.

Support:
- Weekends.
- Configured company holidays.
- Full-day leave.
- Optional half-day leave.

Do not hardcode assumptions about working days or holidays.

If the organization has not configured its working week or holidays, use a clearly documented default and make the rules configurable.

Display the calculation to the employee before submission.

For example:

Leave type: Casual Leave
From: 10 November
To: 11 November
Working days requested: 2
Available balance: 8 days

This is an illustrative example only. Actual values must come from the database.

### Validation

Prevent:
- Missing required fields.
- Invalid date ranges.
- End dates earlier than start dates.
- Duplicate or conflicting leave submissions.
- Requests exceeding the available balance, where the policy prohibits them.
- Leave requests for inactive employees.
- Unauthorized changes to request ownership.
- Unsupported half-day combinations.

Perform validation on both the client and server.

Do not rely on frontend validation alone.

### Submission behavior

On submission:

1. Validate the request.
2. Recalculate leave days on the server.
3. Check the employee's current balance.
4. Check for conflicting requests.
5. Persist the request transactionally.
6. Display a success notification.
7. Refresh the employee dashboard and leave history.

Prevent duplicate submissions caused by repeated clicks or network retries.

Provide a clear confirmation screen or success message.

---

## 8. Leave Request Lifecycle

Implement a well-defined leave request lifecycle.

Support the following statuses:

- Pending.
- Approved.
- Rejected.
- Cancelled.

The initial workflow should work without a manager approval feature.

Recommended behavior:

- An employee submits a request.
- The request is recorded as Pending.
- The administrator can review and manage the request.
- The administrator can approve or reject it.
- An employee can cancel a request when permitted by the configured policy.
- Administrators can make authorized corrections.

When a request is rejected, record the rejection reason or administrative comment where applicable.

When a request is cancelled, retain its history rather than deleting the record.

Record who performed each action and when it occurred.

Approved leave must not be deducted twice.

Pending leave must not automatically be treated as consumed leave.

Cancelling or rejecting a request must correctly update the effective balance.

For requests covering past dates, define the behavior explicitly and follow the organization's configured policy.

Use database transactions to ensure that concurrent actions cannot corrupt leave balances.

---

## 9. Leave Balance Management

Build a reliable leave balance calculation system.

### Configurable leave types

Examples include:

- Casual Leave.
- Sick Leave.
- Earned Leave.
- Privilege Leave.
- Unpaid Leave.

These are examples, not mandatory categories.

Administrators should be able to create, edit, activate, or deactivate leave types.

Each leave type should support appropriate settings, including:

- Name.
- Description.
- Paid or unpaid classification.
- Annual entitlement.
- Whether a balance is maintained.
- Whether half-day leave is permitted.
- Whether negative balances are allowed.
- Carry-forward eligibility.
- Maximum carry-forward limit.
- Applicable leave year.
- Applicable working-day calculation rules.

Avoid implementing a complex policy engine prematurely. Implement the initial policy requirements cleanly and document any limitations.

### Balance calculation

Implement a central, reusable balance calculation service.

Do not duplicate balance calculations across frontend components and API handlers.

The calculation must distinguish between:
- Entitlement.
- Approved leave taken.
- Approved future leave.
- Pending leave.
- Available balance.

Pending requests should be displayed separately. Do not deduct them as consumed leave.

Avoid double-counting approved leave that falls in the future.

Support unpaid leave without incorrectly reducing paid leave balances.

Use precise decimal or integer-based day calculations where appropriate.

For half-day support, use consistent increments.

### Administrative adjustments

Administrators should be able to adjust leave balances when authorized.

Require:
- Employee.
- Leave type.
- Adjustment amount.
- Reason.
- Administrator identity.
- Timestamp.

Maintain an adjustment ledger.

Never silently overwrite an employee's leave balance without preserving the adjustment history.

---

## 10. Leave Calendar

Build a modern, interactive leave calendar.

Provide:
- Month view.
- Week view.
- Agenda or list view.
- Previous and next navigation.
- A button to return to today.
- Filters by employee, leave type, and status where appropriate.
- A responsive layout.

### Employee calendar

Employees should see:
- Their own leave.
- Relevant team leave.
- Company holidays, when configured.

Do not reveal private leave reasons.

### Administrator calendar

Administrators should see organization-wide leave information.

Include:
- Employee name.
- Leave dates.
- Leave type.
- Request status.

Use consistent, accessible colors to distinguish leave types or statuses.

Provide a legend.

Clicking an event should open an appropriate details panel or dialog.

Only display records the current user is authorized to see.

The calendar must use actual database records.

Do not render fake events when there is no leave data.

---

## 11. Administrator Dashboard

Create a centralized dashboard designed for a small organization.

### Summary cards

Display:
- Total active employees.
- Employees on leave today.
- Upcoming approved leave.
- Pending leave requests.
- Leave requests submitted this month.

### Pending requests

Provide a table with:
- Employee.
- Leave type.
- Start date.
- End date.
- Requested days.
- Submission date.
- Current status.
- Available actions.

Actions should include viewing details and, where appropriate, approving, rejecting, or cancelling a request.

### Employee overview

Display:
- Employee name.
- Employee ID.
- Email.
- Department or team.
- Designation.
- Role.
- Employment status.

Support:
- Search.
- Filtering.
- Sorting.
- Pagination.

Use a suitable empty state when there is no data.

### Recent activity

Show relevant administrative and leave-management activities, including:
- New leave requests.
- Approved or rejected requests.
- Employee account changes.
- Leave balance adjustments.

The dashboard must display accurate information derived from the database.

---

## 12. Employee Management

Create an employee management module for administrators.

Employee fields should include:

- Unique employee ID.
- Full name.
- Work email.
- Department.
- Designation.
- Date of joining.
- Employment status.
- Assigned role.
- Reporting manager, reserved for the future manager workflow.

Support:
- Adding employees.
- Editing employee details.
- Viewing employee profiles.
- Activating and deactivating employees.
- Viewing leave history.
- Viewing leave balances.

Prevent duplicate employee IDs and duplicate work email addresses.

Use appropriate database constraints.

Deactivating an employee must not delete historical leave records.

Only authorized administrators should be able to change roles.

Maintain audit history for sensitive employee changes.

---

## 13. Reports and Analytics

Implement a simple reporting module.

Reports should include:

- Leave utilization by employee.
- Leave utilization by leave type.
- Leave requests by status.
- Monthly leave summary.
- Upcoming leave.
- Employee leave balances.

Provide filters for:
- Date range.
- Employee.
- Department.
- Leave type.
- Status.

Use clear tables and simple charts.

Include CSV export for authorized users.

Protect exported files and ensure they contain only information the user is permitted to access.

Avoid excessive analytics that do not provide practical value to a small organization.

---

## 14. Database Design

Use PostgreSQL and Prisma ORM if starting from scratch.

Design a normalized, maintainable schema.

At a minimum, evaluate the following entities:

### User
- id
- email
- password hash or authentication-provider reference
- role
- active status
- createdAt
- updatedAt

### Employee
- id
- employeeCode
- userId
- fullName
- department
- designation
- joiningDate
- managerId, nullable
- employmentStatus
- createdAt
- updatedAt

### LeaveType
- id
- name
- description
- paid status
- balance tracking configuration
- entitlement configuration
- half-day configuration
- carry-forward configuration
- active status
- createdAt
- updatedAt

### LeaveRequest
- id
- employeeId
- leaveTypeId
- startDate
- endDate
- requestedDays
- half-day information, if applicable
- reason
- status
- submittedAt
- reviewedBy, nullable
- reviewedAt, nullable
- reviewComment, nullable
- createdAt
- updatedAt

### LeaveEntitlement
- id
- employeeId
- leaveTypeId
- leaveYear
- entitledDays
- createdAt
- updatedAt

### LeaveBalanceAdjustment
- id
- employeeId
- leaveTypeId
- leaveYear
- adjustmentDays
- reason
- adjustedBy
- createdAt

### Holiday
- id
- name
- holidayDate
- description
- active status

### AuditLog
- id
- actorUserId
- action
- entityType
- entityId
- relevant change metadata
- timestamp

Add any supporting entities required for reliable implementation.

Use appropriate:
- Foreign keys.
- Unique constraints.
- Indexes.
- Transactions.
- Referential integrity.
- Database migrations.

Use consistent timestamps and clearly define how dates are stored and displayed.

Leave requests are date-based, so avoid timezone conversion bugs that can shift a requested date.

Document the relationship between employees, login accounts, leave requests, entitlements, and adjustments.

Do not store a manually maintained available balance as the only source of truth.

Calculate balances from entitlements, approved leave, and adjustments according to the applicable policy.

If cached balance values are introduced later for performance, they must be reconciled against the authoritative records.

---

## 15. Security Requirements

Security is a priority, even though this is an internal application.

Implement:

- Server-side authentication.
- Server-side authorization.
- Role-based access control.
- Input validation.
- Parameterized database operations through the ORM.
- Secure password handling.
- Protection against cross-site scripting.
- Appropriate CSRF protection where applicable.
- Secure cookie settings.
- Rate limiting for authentication endpoints.
- Safe error handling.
- Secure environment-variable management.
- Least-privilege database access.
- Audit logging for sensitive operations.
- Protection against unauthorized record access.
- Safe file handling if file uploads are introduced later.

Never expose database credentials, secrets, password hashes, or internal stack traces to the browser.

Do not trust employee IDs, roles, or balance values supplied by the client.

Derive the authenticated user identity from the verified server-side session.

Ensure an employee cannot access another employee's private records by modifying a URL or API parameter.

Ensure administrators cannot accidentally bypass required business validation.

Do not log passwords, authentication tokens, or unnecessary personal information.

Document production security configuration and deployment prerequisites.

---

## 16. Technical Architecture

Keep the architecture simple enough for a small organization to maintain.

Use clear separation between:

- UI components.
- Application pages.
- Authentication.
- API or server actions.
- Business services.
- Database access.
- Validation schemas.
- Authorization policies.
- Shared types and utilities.

Create a centralized leave service responsible for:

- Calculating requested leave days.
- Validating leave requests.
- Calculating balances.
- Creating requests.
- Cancelling requests.
- Approving and rejecting requests.
- Processing balance adjustments.

Use transactions for operations that update related records.

Avoid putting complex business rules directly inside React components.

Avoid creating unnecessary microservices for this application.

Prefer a modular monolithic architecture.

Use strict TypeScript settings and maintain readable code.

---

## 17. Error Handling and User Feedback

Every important action must provide clear feedback.

Examples:

- Leave request submitted successfully.
- Leave request cancelled successfully.
- Leave balance updated successfully.
- Employee created successfully.
- The selected dates overlap an existing request.
- Insufficient leave balance.
- You do not have permission to perform this action.
- The requested record could not be found.

Provide:
- Loading indicators.
- Disabled buttons during submissions.
- Inline field validation.
- Confirmation dialogs for destructive or consequential actions.
- Useful empty states.
- Recoverable error messages.

Do not expose raw backend errors to users.

Do not silently ignore failed requests.

---

## 18. Testing Requirements

Create meaningful tests for business logic and authorization.

At a minimum, test:

### Authentication and permissions
- Unauthenticated users cannot access protected pages.
- Employees cannot access administrator APIs.
- Employees cannot modify another employee's requests.
- Unauthorized users cannot change roles or balances.

### Leave calculation
- Single-day leave.
- Multi-day leave.
- Weekend exclusions.
- Holiday exclusions.
- Half-day calculations, if enabled.
- Insufficient balance.
- Unpaid leave.
- Pending requests.
- Approved leave.
- Cancelled and rejected requests.
- Balance adjustments.

### Request lifecycle
- Successful submission.
- Invalid date ranges.
- Conflicting requests.
- Duplicate submission prevention.
- Administrator approval.
- Administrator rejection.
- Employee cancellation.
- Correct balance after each transition.

### Employee management
- Duplicate employee ID prevention.
- Duplicate email prevention.
- Employee deactivation.
- Historical data retention.

Test the actual application behavior rather than merely checking whether components render.

---

## 19. Implementation Plan

Implement the application incrementally.

### Phase 1: Project foundation
- Inspect the existing repository.
- Confirm the existing framework and project structure.
- Establish the architecture.
- Configure the design system.
- Set up the database.
- Implement migrations.
- Configure authentication.
- Implement role-based access control.

### Phase 2: Core leave functionality
- Employee dashboard.
- Leave types.
- Leave entitlements.
- Leave application form.
- Leave history.
- Leave balance calculations.
- Leave cancellation.

### Phase 3: Administrator functionality
- Administrator dashboard.
- Employee management.
- Leave request management.
- Leave balance adjustments.
- Leave policy configuration.
- Audit history.

### Phase 4: Calendar and reports
- Interactive leave calendar.
- Calendar filters.
- Leave analytics.
- CSV exports.

### Phase 5: Validation and hardening
- Automated tests.
- Authorization testing.
- Error handling.
- Responsive design verification.
- Accessibility improvements.
- Performance checks.
- Security review.
- Documentation.

Build and verify each phase before moving to the next.

Do not generate the entire application as a single unstructured block of code.

---

## 20. Cursor Agent Instructions

Before implementing anything:

1. Inspect the current repository and identify the framework, dependencies, existing components, and conventions.
2. If the repository is empty, initialize the recommended stack.
3. Create a concise implementation plan.
4. Identify important assumptions that require configuration.
5. Propose the database schema and application structure.

Then proceed with implementation.

Do not stop after presenting the plan. Continue implementing the application unless a genuine blocker requires clarification.

Prefer small, coherent changes that can be tested.

After each major phase:

- Run the relevant tests.
- Run linting.
- Run TypeScript checks.
- Fix errors before proceeding.
- Verify that existing functionality still works.

Do not replace existing project files unnecessarily.

Do not introduce dummy authentication or pretend that frontend-only authorization is secure.

Do not use hardcoded employee data, leave balances, or requests as production data.

Seed data may be provided for local development only, and development seed data must be clearly separated from production.

Use database migrations for schema changes.

Provide an `.env.example` file containing variable names and placeholder values only.

Never commit secrets.

If a required external service is not configured, document the missing configuration and provide a safe local development workflow.

---

## 21. Definition of Done

The initial release is complete when:

1. An authorized employee can log in.
2. The employee can view their leave balance.
3. The employee can submit a leave request.
4. The request is saved in the database.
5. The employee can view their request history.
6. The employee can cancel eligible requests.
7. Leave calculations follow configured rules.
8. The employee can view the leave calendar.
9. An administrator can log in.
10. The administrator can view all employees.
11. The administrator can create and update employee records.
12. The administrator can manage leave requests.
13. The administrator can configure leave types and entitlements.
14. Balance adjustments are recorded in an audit trail.
15. Employee and administrator permissions are enforced on the server.
16. The application is responsive and visually polished.
17. Core business logic and authorization tests pass.
18. Database setup and migrations are documented.
19. Local development setup is documented.
20. The application can be started and used by following the README.

At completion, provide:

- Architecture overview.
- Database schema summary.
- Implemented features.
- Features intentionally deferred to later phases.
- Environment setup instructions.
- Database migration and seed instructions.
- Test execution instructions.
- Local startup instructions.
- Production deployment prerequisites.
- Any known limitations.

## Final Instruction

Build PeopleHub as a polished, secure, maintainable HR Self-Service Portal for a small organization.

Prioritize usability, correctness, simplicity, maintainability, and security.

The experience should be pleasant for employees and efficient for administrators.

Make sensible implementation decisions, document assumptions, and deliver working functionality rather than stopping at a mockup.