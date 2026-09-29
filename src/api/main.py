"""FastAPI application for the Nifty100 analytics project."""
import time, logging, sqlite3
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.common import connect, tables
from src.api.routers import companies, screener, sectors, peers, valuation, portfolio, documents, health

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log=logging.getLogger('nifty100.api'); START=time.time()
app=FastAPI(title='Nifty100 Analytics API',version='1.0.0',description='Sprint 6 REST API')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=False,allow_methods=['*'],allow_headers=['*'])
@app.middleware('http')
async def request_logger(request:Request,call_next):
    """Log HTTP method, path and response time for every request."""
    t=time.perf_counter(); response=await call_next(request); log.info('%s %s -> %s %.2fms',request.method,request.url.path,response.status_code,(time.perf_counter()-t)*1000); return response
app.include_router(companies.router,prefix='/api/v1')
app.include_router(screener.router,prefix='/api/v1')
app.include_router(sectors.router,prefix='/api/v1')
app.include_router(peers.router,prefix='/api/v1')
app.include_router(valuation.router,prefix='/api/v1')
app.include_router(portfolio.router,prefix='/api/v1')
app.include_router(documents.router,prefix='/api/v1')
app.include_router(health.router,prefix='/api/v1')
