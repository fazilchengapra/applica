export function createLoginOtpSms(otp: string, phone: string) {
  return {
    body:`Your login OTP is ${otp}. It will expire in 5 minutes. Do not share this code with anyone.`,
    to: phone
};
}

export function createPhoneVerificationOtpSms(otp: string, phone: string) {
  return {
    body: `Your verification code is ${otp}. This code expires in 5 minutes. Please do not share it with anyone.`,
    to: phone,
  };
}