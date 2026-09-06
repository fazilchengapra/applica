export function createRegistrationCompletedEmailPayload(
  email: string
) {
  return {
    to: email,
    subject: "Registration Completed Successfully",
    html: `
      <h1>Welcome!</h1>
      <p>Your registration has been completed successfully.</p>
      <p>Your account is now ready to use.</p>
      <p>Thank you for joining us!</p>
    `,
    text: `
Welcome!

Your registration has been completed successfully.
Your account is now ready to use.

Thank you for joining us!
    `,
  };
}