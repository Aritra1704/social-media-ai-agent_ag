package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.stereotype.Component;

@SpringBootApplication
@Component
public class SkillTest6App implements CommandLineRunner {
    @Override
    public void run(String... args) throws Exception {
        System.out.println("Skill Test 6 running");
    }

    public static void main(String[] args) {
        SpringApplication.run(SkillTest6App.class, args);
    }
}