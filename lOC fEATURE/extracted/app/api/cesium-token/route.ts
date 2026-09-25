import { NextResponse } from 'next/server'

export async function GET() {
  const token = process.env.JWT_2 || process.env.JWT

  if (!token) {
    return NextResponse.json({ error: 'Cesium token is not configured' }, { status: 503 })
  }

  return NextResponse.json({ token }, { headers: { 'Cache-Control': 'no-store' } })
}
