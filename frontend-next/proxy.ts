import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

type Role = 'rep' | 'trainer' | 'manager' | 'admin'

function roleHome(role: Role): string {
  if (role === 'rep') return '/dashboard'
  if (role === 'trainer' || role === 'manager') return '/admin'
  if (role === 'admin') return '/super'
  return '/dashboard'
}

function forbidden(): NextResponse {
  return new NextResponse(
    `<!doctype html><html><head><title>403 Forbidden</title>
    <style>body{background:#10141a;color:#e8eaed;font-family:system-ui;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;flex-direction:column;gap:12px;}
    h1{font-size:2rem;color:#2ddbde;margin:0}p{color:#9aa0a6;margin:0}a{color:#2ddbde;font-size:.875rem}</style></head>
    <body><h1>403</h1><p>You don&apos;t have permission to access this page.</p><a href="/dashboard">&larr; Back to dashboard</a></body></html>`,
    { status: 403, headers: { 'content-type': 'text/html' } }
  )
}

export async function proxy(request: NextRequest) {
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

  // Public paths — always pass through
  const publicPaths = ['/auth', '/join']
  const isPublic = publicPaths.some(p => pathname.startsWith(p))
  if (isPublic) return response

  // Root redirect based on role
  if (pathname === '/') {
    if (!user) {
      return NextResponse.redirect(new URL('/auth/login', request.url))
    }
    const role = (user.user_metadata?.role ?? 'rep') as Role
    return NextResponse.redirect(new URL(roleHome(role), request.url))
  }

  // Protected route categories
  const protectedPrefixes = ['/dashboard', '/session', '/library', '/admin', '/super']
  const requiresAuth = protectedPrefixes.some(p => pathname.startsWith(p))

  // Unauthenticated on protected route → login
  if (!user && requiresAuth) {
    const loginUrl = new URL('/auth/login', request.url)
    loginUrl.searchParams.set('next', pathname)
    return NextResponse.redirect(loginUrl)
  }

  if (!user) return response

  const role = (user.user_metadata?.role ?? 'rep') as Role

  // /admin/* — trainer, manager, or admin only
  if (pathname.startsWith('/admin')) {
    if (role !== 'trainer' && role !== 'manager' && role !== 'admin') {
      return forbidden()
    }
  }

  // /super/* — admin only
  if (pathname.startsWith('/super')) {
    if (role !== 'admin') {
      return forbidden()
    }
  }

  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
}
