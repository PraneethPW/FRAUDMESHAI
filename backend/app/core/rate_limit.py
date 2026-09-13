"""Bounded per-process auth throttling for the existing single-worker deployment."""
import time
from collections import OrderedDict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class AuthRateLimit(BaseHTTPMiddleware):
    def __init__(self,app):
        super().__init__(app);self.attempts=OrderedDict()
    async def dispatch(self,request,call_next):
        limits={'/api/v1/auth/login':60,'/api/v1/auth/register':60,'/api/v1/auth/forgot-password':6,'/api/v1/auth/reset-password':15}
        limit=limits.get(request.url.path)
        if request.method=='POST' and limit:
            key=(request.client.host if request.client else 'unknown',request.url.path)
            now=time.monotonic();times=self.attempts.setdefault(key,deque())
            while times and times[0]<now-60: times.popleft()
            if len(times)>=limit: return JSONResponse({'detail':'Too many attempts. Please retry in one minute.'},status_code=429,headers={'Retry-After':'60'})
            times.append(now);self.attempts.move_to_end(key)
            while len(self.attempts)>2048:self.attempts.popitem(last=False)
        return await call_next(request)
