export function createChangeEmailPayload(
  email: string,
  verificationLink: string
) {
  return {
    to: email,
    subject: "Confirm Your New Email Address",
    html: `
      <h1>Confirm Your New Email Address</h1>
      
      <p>You recently requested to change the email address associated with your account.</p>
      
      <p>Please confirm your new email address by clicking the link below:</p>
      
      <a href="${verificationLink}">
        Confirm New Email Address
      </a>
      
      <p>If you did not request this change, please ignore this email or contact support.</p>
    `,
    text: `
You recently requested to change your email address.

Confirm your new email address using this link:
${verificationLink}

If you did not request this change, please ignore this email.
    `,
  };
}