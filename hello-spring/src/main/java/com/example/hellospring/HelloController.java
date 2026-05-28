package com.example.hellospring;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
class HelloController {

    @GetMapping("/hello")
    public String sayHello() {
        return "Hello, Spring!";
    }
}