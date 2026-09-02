export function createEmailChangedConfirmedPayload(
  email: string,
  oldEmail: string
) {
  return {
    to: email,
    subject: "Your Email Address Has Been Changed",
    html: `
      <h1>Email Address Changed Successfully</h1>

      <p>Your account email address has been successfully changed.</p>

      <p>Your previous email address was: <strong>${oldEmail}</strong></p>

      <p>You can now use this email address to access your account.</p>

      <p>If you did not make this change, please contact support immediately to secure your account.</p>
    `,
    text: `
Your email address has been successfully changed.

Your previous email address was: ${oldEmail}

You can now use this email address to access your account.

If you did not make this change, please contact support immediately to secure your account.
    `,
  };
}