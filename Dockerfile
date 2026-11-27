FROM python:3.13-alpine3.24@sha256:9ef1a599f863231c3d91e941389bfdc4a2d6070557243d54df1a4e57015b960e
RUN python -m pip uninstall --yes pip && rm -rf /usr/local/lib/python3.13/ensurepip
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY app/paynest.py app/IRONGATE_CANARY ./
USER 65532:65532
EXPOSE 8080
CMD ["python", "paynest.py", "--host", "0.0.0.0"]
