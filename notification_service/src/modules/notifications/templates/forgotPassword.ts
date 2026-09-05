export function createForgotPasswordEmailPayload(
  email: string,
  resetLink: string,
) {
  return {
    to: email,
    subject: "Reset Your Password",
    html: `
      <h1>Reset Your Password</h1>
      <p>We received a request to reset the password for your account.</p>
      <p>Click the button below to create a new password:</p>
      <p>
        <a href="${resetLink}">Reset Password</a>
      </p>
      <p>This password reset link will expire soon for security reasons.</p>
      <p>If you did not request a password reset, you can safely ignore this email.</p>
    `,
    text: `
Reset Your Password

We received a request to reset the password for your account.

Use the following link to create a new password:

${resetLink}

This password reset link will expire soon for security reasons.

If you did not request a password reset, you can safely ignore this email.
    `,
  };
}
