from fastapi import FastAPI
import data
import monte
import uvicorn


app = FastAPI()
app.include_router(data.router, prefix="/data", tags=["Data"])
app.include_router(monte.router, prefix="/monte", tags=["Monte Carlo"])

# Ensure Server is Up 
@app.get("/")
async def root():
    return {"message": "Main Server is Running"}

if __name__ == "__main__":
    uvicorn.run("server:app", reload=True)