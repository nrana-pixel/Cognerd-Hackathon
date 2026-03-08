import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { notifications } from '@/lib/db/schema';
import { desc, eq } from 'drizzle-orm';
import { auth } from '@/lib/auth';

export async function GET(request: NextRequest) {
  try {
    let userId: string | null = null;
    let userEmail: string | null = null;
    try {
      const session = await auth.api.getSession({ headers: request.headers as any });
      if (session?.user) {
        userId = session.user.id || null;
        userEmail = session.user.email || null;
      }
    } catch {}

    if (!userId && !userEmail) {
      return NextResponse.json({ notifications: [] });
    }

    const where = userId
      ? eq(notifications.userId, userId)
      : eq(notifications.userEmail, userEmail!);

    const rows = await db
      .select()
      .from(notifications)
      .where(where)
      .orderBy(desc(notifications.createdAt));

    return NextResponse.json({ notifications: rows });
  } catch (e) {
    console.error('Failed to list notifications', e);
    return NextResponse.json({ error: 'Failed to list notifications' }, { status: 500 });
  }
}
