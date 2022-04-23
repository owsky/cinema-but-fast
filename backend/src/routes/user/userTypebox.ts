import { Type, Static } from "@sinclair/typebox"

export const User = Type.Object({
  email: Type.String(),
  full_name: Type.String(),
  user_role: Type.Optional(Type.String()),
})
export type UserType = Static<typeof User>