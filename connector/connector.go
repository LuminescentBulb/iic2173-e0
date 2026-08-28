package main

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"time"

	rmq "github.com/rabbitmq/rabbitmq-amqp-go-client/pkg/rabbitmqamqp"
)

type Demand struct {
	City   string  `json:"city"`
	Demand float64 `json:"demand"`
	Unit   string  `json:"unit"`
}

type PackageBody struct {
	Demands     []Demand               `json:"demands"`
	ValidUntil  time.Time              `json:"validUntil"`
	MetaContent string                 `json:"metaContent"`
	Constraints map[string]interface{} `json:"constraints"`
}

type Event struct {
	IDPK        string      `json:"idpk"`
	Type        string      `json:"type"`
	PackageBody PackageBody `json:"packageBody"`
	ReceivedAt  time.Time   `json:"receivedAt"`
}

func main() {
	brokerURI := os.Getenv("RABBITMQ_URL")
	for {
		err := connectConsume(brokerURI)
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
		processErr := processMessage(msg.GetData())
		if processErr != nil {
			return fmt.Errorf("Error processing message: %v", processErr)
		}

		err = delivery.Accept(ctx)
		if err != nil {
			return fmt.Errorf("failed to accept message: %v", err)
		}
	}
}

var httpClient = &http.Client{
	Timeout: 10 * time.Second,
}

func processMessage(body []byte) error {
	// parse json message into Event struct
	var event Event

	if err := json.Unmarshal(body, &event); err != nil {
		return fmt.Errorf("failed to unmarshal message: %v", err)
	}

	// add receivedAt timestamp to the event
	event.ReceivedAt = time.Now().UTC()

	// convert Event struct to json
	jsonBody, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %v", err)
	}

	// log.Printf("Processed message: %s", string(jsonBody))
	// send POST req to master
	masterURL := os.Getenv("MASTER_URL")
	if masterURL == "" {
		return fmt.Errorf("MASTER_URL is not set")
	}

	resp, err := httpClient.Post(
		masterURL+"/events",
		"application/json",
		bytes.NewBuffer(jsonBody),
	)
	if err != nil {
		return fmt.Errorf("failed to send POST request to master: %v", err)
	}
	defer resp.Body.Close()

	return nil

}
