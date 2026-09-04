export function createPasswordChangedEmailPayload(email: string) {
  return {
    to: email,
    subject: "Your Password Has Been Changed",
    html: `
      <h1>Password Changed Successfully</h1>
      <p>Your account password has been changed successfully.</p>
      <p>You can now use your new password to sign in to your account.</p>
      <p>If you did not make this change, please contact our support team immediately.</p>
    `,
    text: `
Password Changed Successfully

Your account password has been changed successfully.
You can now use your new password to sign in to your account.

If you did not make this change, please contact our support team immediately.
    `,
  };
}