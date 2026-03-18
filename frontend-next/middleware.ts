import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request: { headers: request.headers } })
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll() },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value))
          response = NextResponse.next({ request })
          cookiesToSet.forEach(cookie =>
            response.cookies.set(cookie.name, cookie.value, cookie.options))
        },
      },
    }
  )
  const { data: { user } } = await supabase.auth.getUser()
  const { pathname } = request.nextUrl
  const publicPaths = ['/auth', '/join', '/']
  const isPublic = publicPaths.some(p => pathname.startsWith(p))
  if (!user && !isPublic) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }
  return response
}

export const config = { matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'] }
