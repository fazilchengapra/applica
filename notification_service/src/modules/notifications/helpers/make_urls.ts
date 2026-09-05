import {env} from '../../../config/env'

export const get_forgot_pass_url=(raw_token: string): string => {
    return `${env.FRONTEND_URL}/forgot-password?token=${raw_token}`
}