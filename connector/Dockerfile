FROM golang:1.25-alpine
WORKDIR /app

# Download and run Go modules
COPY go.mod go.sum ./
RUN go mod download

COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -o /connector

CMD ["/connector"]
