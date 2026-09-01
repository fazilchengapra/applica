export function createVerificationEmailPayload(
  email: string,
  verificationLink: string
) {
  return {
    to: email,
    subject: "Account Verification",
    html: `
      <h1>Verify your account</h1>
      <p>Please click the link below:</p>
      <a href="${verificationLink}">
        Verify Account
      </a>
    `,
    text: `Your verification link is ${verificationLink}`,
  };
}