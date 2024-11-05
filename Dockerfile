FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
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

COPY . /opt/osiris-cloud
WORKDIR /opt/osiris-cloud

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN npm install
RUN npm run build
RUN npx tailwindcss -i ./static/assets/style.css -o ./static/dist/css/output.css

EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=30s CMD curl -f http://localhost:8000/healthz || exit 1

ENTRYPOINT ["/opt/osiris-cloud/entrypoint.sh"]

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "--proxy-headers", "core.asgi:application"]
