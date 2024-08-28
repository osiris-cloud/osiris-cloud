FROM python:3.12

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DOPPLER_TOKEN=$DOPPLER_TOKEN

# Install node 18 and npm
RUN set -uex; \
    apt-get update; \
    apt-get install -y ca-certificates curl gnupg; \
    mkdir -p /etc/apt/keyrings; \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
     | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg; \
    NODE_MAJOR=18; \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" \
     > /etc/apt/sources.list.d/nodesource.list; \
    apt-get update; \
    apt-get install nodejs -y;

# Install Doppler CLI
RUN apt-get install -y apt-transport-https && \
    curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | gpg --dearmor -o /usr/share/keyrings/doppler-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/doppler-archive-keyring.gpg] https://packages.doppler.com/public/cli/deb/debian any-version main" | tee /etc/apt/sources.list.d/doppler-cli.list && \
    apt-get update && \
    apt-get -y install doppler

WORKDIR /osiris-cloud
COPY . /osiris-cloud/

# install python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install Modules, Webpack and Tailwind set up
RUN npm i
RUN npm run build
RUN npx tailwindcss -i ./static/assets/style.css -o ./static/dist/css/output.css

RUN doppler secrets download --no-file --format env > .env

RUN python manage.py makemigrations
RUN python manage.py manage.py migrate

# Manage Assets & DB
RUN python manage.py collectstatic --no-input

# Expose the port Daphne will run on
EXPOSE 8000

# See if app works
HEALTHCHECK --interval=10s --timeout=30s CMD curl -f http://localhost:8000/ || exit 1

# Run Daphne
CMD ["doppler", "run", "--", "daphne", "-b", "0.0.0.0", "-p", "8000", "--proxy-headers", "core.asgi:application"]
