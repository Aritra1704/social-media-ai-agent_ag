package com.example;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class SkillTest2App implements CommandLineRunner {

    public static void main(String[] args) {
        SpringApplication.run(SkillTest2App.class, args);
    }

    @Override
    public void run(String... args) throws Exception {
        System.out.println("Skill Test 2 running");
    }
}