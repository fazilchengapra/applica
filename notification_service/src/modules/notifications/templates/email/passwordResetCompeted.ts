export function createPasswordResetCompletedEmailPayload(email: string) {
  return {
    to: email,
    subject: "Your Password Has Been Reset",
    html: `
      <h1>Password Reset Successfully</h1>
      <p>Your account password has been reset successfully.</p>
      <p>You can now sign in to your account using your new password.</p>
      <p>If you did not reset your password, please contact our support team immediately.</p>
    `,
    text: `
Password Reset Successfully

Your account password has been reset successfully.

You can now sign in to your account using your new password.

If you did not reset your password, please contact our support team immediately.
    `,
  };
}