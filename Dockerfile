# Use a base image with Python and uv pre-installed
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.6.12 /uv /uvx /bin/

# Copy the project into the image
ADD . /app

# Set the working directory
WORKDIR /app

EXPOSE 8050

# Install project dependencies using uv
RUN uv sync --locked

# Set the default command to run the backtest
CMD ["uv", "run", "-m", "back_test.dashboard"]