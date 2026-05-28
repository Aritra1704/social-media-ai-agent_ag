package com.example;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class HelloApp {

    public static void main(String[] args) {
        SpringApplication.run(HelloApp.class, args);
    }

    @Bean
    public CommandLineRunner commandLineRunner() {
        return args -> System.out.println("Hello AI world");
    }
}