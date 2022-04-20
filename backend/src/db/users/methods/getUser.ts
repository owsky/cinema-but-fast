import { PostgresDb } from "fastify-postgres"
import User from "../../../models/user"
import getUserQuery from "../queries/getUserQuery"

export default async function getUser(
  db: PostgresDb & Record<string, PostgresDb>,
  email: string
): Promise<User | null> {
  try {
    const client = await db.connect()
    const { rows } = await getUserQuery(client, email)
    const user: User = {
      email: rows.at(0).email,
      full_name: rows.at(0).full_name,
      password: rows.at(0).password,
      user_role: rows.at(0).user_role,
    }

    client.release()
    return user
  } catch (e) {
    console.error(e)
    return null
  }
}
