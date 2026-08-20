package main

import (
	"context"
	"crypto/tls"
	"errors"
	"fmt"
	"log"
	"net/url"
	"os"
	"time"

	"github.com/joho/godotenv"
	rmq "github.com/rabbitmq/rabbitmq-amqp-go-client/pkg/rabbitmqamqp"
)


type Demand struct {
	City   string
	Demand float64
	Unit   string
}

type PackageBody struct {
	Demands     []Demand
	ValidUntil  time.Time
	MetaContent string
	Constraints map[string]interface{}
}

type Event struct {
	IDPK string
	Type string
	PackageBody PackageBody
}

func main() {
	err := godotenv.Load(".env")
	if err != nil {
		log.Panicf("Error loading .env file: %v", err)
	}

	brokerURI := os.Getenv("RABBITMQ_URL")
	for {
		err = connectConsume(brokerURI)
		if err != nil {
			log.Printf("RabbitMQ Connection lost: %v", err)
		}

		time.Sleep(5 * time.Second)
	}
}

func connectConsume(brokerURI string) error {
	u, err := url.Parse(brokerURI)
	if err != nil {
		return fmt.Errorf("invalid RABBITMQ_URL: %v", err)
	}

	connOpts := &rmq.AmqpConnOptions{
		TLSConfig: &tls.Config{ServerName: u.Hostname()},
	}

	ctx := context.Background()
	env := rmq.NewEnvironment(brokerURI, connOpts)
	conn, err := env.NewConnection(ctx)
	if err != nil {
		return fmt.Errorf("failed to connect to RabbitMQ: %v", err)
	}
	defer func() {
		_ = env.CloseConnections(context.Background())
	}()

	consumer, err := conn.NewConsumer(ctx, "observer.27.q", nil)
	if err != nil {
		return fmt.Errorf("failed to create consumer: %v", err)
	}
	defer func() { _ = consumer.Close(context.Background()) }()

	log.Printf(" [*] Waiting for messages. To exit press CTRL+C")
	for {
		delivery, err := consumer.Receive(ctx)
		if err != nil {
			if errors.Is(err, context.Canceled) {
				return nil
			}
			return fmt.Errorf("failed to receive a message: %v", err)
		}
		msg := delivery.Message()
		var body string
		if len(msg.Data) > 0 {
			body = string(msg.Data[0])
		}
		log.Printf("Received a message: %s", body)
		err = delivery.Accept(ctx)
		if err != nil {
			return fmt.Errorf("failed to accept message: %v", err)
		}
	}
}
