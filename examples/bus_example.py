"""Example application using the LLMgine architecture.

This example demonstrates the integration of the ObservabilityBus and MessageBus
for building event-driven applications.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from llmgine.bootstrap import ApplicationBootstrap, ApplicationConfig
from llmgine.messages.commands import Command, CommandResult
from llmgine.messages.events import Event
from llmgine.observability.events import LogLevel, TraceEvent
from llmgine.observability.handlers import (
    InMemoryMetricsHandler,
    InMemoryTraceHandler,
    ConsoleTraceHandler
)


#
# Define our domain models
#

@dataclass
class User:
    """A user in the system."""
    
    id: str
    name: str
    email: str
    preferences: Dict[str, Any] = field(default_factory=dict)


#
# Define commands and their results
#

@dataclass
class UserRegistrationCommand(Command):
    """Command to register a new user."""
    
    name: str = ""
    email: str = ""
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserGreetingCommand(Command):
    """Command to greet a user."""
    
    user_id: str = ""
    greeting_type: str = "standard"


@dataclass
class SendEmailCommand(Command):
    """Command to send an email to a user."""
    
    user_id: str = ""
    subject: str = ""
    body: str = ""


#
# Define events
#

@dataclass
class UserRegisteredEvent(Event):
    """Event emitted when a user has been registered."""
    
    user_id: str = ""
    name: str = ""
    email: str = ""


@dataclass
class UserGreetedEvent(Event):
    """Event emitted when a user has been greeted."""
    
    user_id: str = ""
    greeting_message: str = ""


@dataclass
class EmailSentEvent(Event):
    """Event emitted when an email has been sent."""
    
    user_id: str = ""
    email: str = ""
    subject: str = ""


#
# Application implementation
#

class UserDatabase:
    """Simple in-memory user database."""
    
    def __init__(self):
        """Initialize the database."""
        self.users: Dict[str, User] = {}
        self.next_id = 1
        
    def add_user(self, name: str, email: str, preferences: Dict[str, Any] = None) -> User:
        """Add a user to the database.
        
        Args:
            name: User name
            email: User email
            preferences: Optional user preferences
            
        Returns:
            The created user
        """
        user_id = f"user_{self.next_id}"
        self.next_id += 1
        
        user = User(
            id=user_id,
            name=name,
            email=email,
            preferences=preferences or {}
        )
        
        self.users[user_id] = user
        return user
        
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID.
        
        Args:
            user_id: The user ID to retrieve
            
        Returns:
            The user, or None if not found
        """
        return self.users.get(user_id)
        
    def list_users(self) -> List[User]:
        """List all users.
        
        Returns:
            List of users
        """
        return list(self.users.values())


class EmailService:
    """Simple mock email service."""
    
    def __init__(self):
        """Initialize the email service."""
        self.sent_emails: List[Dict[str, Any]] = []
        
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            
        Returns:
            True if the email was sent
        """
        # Simulate network delay
        time.sleep(0.1)
        
        self.sent_emails.append({
            "to": to_email,
            "subject": subject,
            "body": body,
            "sent_at": time.time()
        })
        
        return True


class ExampleApplication(ApplicationBootstrap):
    """Example application demonstrating LLMgine architecture."""
    
    def __init__(self) -> None:
        """Initialize the example application."""
        # Create custom config with enhanced observability
        config = ApplicationConfig(
            log_level=LogLevel.DEBUG,
            log_dir="logs/example",
            console_logging=True,
            file_logging=True,
            metrics_enabled=True,
            tracing_enabled=True
        )
        
        # Initialize the bootstrap with our config
        super().__init__(config)
        
        # Initialize our domain services
        self.user_db = UserDatabase()
        self.email_service = EmailService()
        
        # Add memory-based handlers for metrics and traces
        self.metrics_handler = InMemoryMetricsHandler()
        self.trace_handler = InMemoryTraceHandler()
        self.obs_bus.add_handler(self.metrics_handler)
        self.obs_bus.add_handler(self.trace_handler)
        
        # Add extra trace handler to see spans in console
        self.obs_bus.add_handler(ConsoleTraceHandler())
    
    def _register_command_handlers(self) -> None:
        """Register command handlers for our application."""
        # User registration flow
        self.register_command_handler(
            UserRegistrationCommand, self.handle_user_registration
        )
        
        # User greeting flow
        self.register_command_handler(
            UserGreetingCommand, self.handle_user_greeting
        )
        
        # Email sending flow
        self.register_command_handler(
            SendEmailCommand, self.handle_send_email
        )
    
    def _register_event_handlers(self) -> None:
        """Register event handlers for our application."""
        # When a user is registered, send welcome email
        self.register_event_handler(
            UserRegisteredEvent, self.handle_user_registered
        )
        
        # When a user is greeted, log it
        self.register_event_handler(
            UserGreetedEvent, self.handle_user_greeted
        )
        
        # When an email is sent, log it
        self.register_event_handler(
            EmailSentEvent, self.handle_email_sent
        )
        
        # Track all trace events for demonstration
        self.register_event_handler(
            TraceEvent, self.handle_trace_event
        )
    
    def handle_user_registration(self, command: UserRegistrationCommand) -> CommandResult:
        """Handle user registration command.
        
        Args:
            command: User registration command
            
        Returns:
            Command result
        """
        # Start a custom trace span (note: commands are already traced automatically)
        span = self.obs_bus.start_trace(
            "database_operation", 
            {"operation": "add_user", "name": command.name}
        )
        
        # Add user to database
        user = self.user_db.add_user(
            name=command.name,
            email=command.email,
            preferences=command.preferences
        )
        
        # End the trace span
        self.obs_bus.end_trace(span, "success")
        
        # Record a metric for user registrations
        self.obs_bus.metric(
            name="user_registrations", 
            value=1, 
            tags={"source": "api"}
        )
        
        # Return success result
        return CommandResult(
            command_id=command.id,
            success=True,
            result=user,
            metadata={"user_id": user.id}
        )
    
    def handle_user_greeting(self, command: UserGreetingCommand) -> CommandResult:
        """Handle the user greeting command.
        
        Args:
            command: The greeting command
            
        Returns:
            Command result
        """
        # Get the user from the database
        user = self.user_db.get_user(command.user_id)
        
        if not user:
            return CommandResult(
                command_id=command.id,
                success=False,
                error=f"User not found with ID: {command.user_id}"
            )
        
        # Generate the greeting based on type
        if command.greeting_type == "formal":
            greeting = f"Good day, {user.name}. It is a pleasure to meet you."
        elif command.greeting_type == "casual":
            greeting = f"Hey {user.name}! What's up?"
        else:
            greeting = f"Hello {user.name}, welcome to LLMgine!"
        
        # Create the result
        return CommandResult(
            command_id=command.id,
            success=True,
            result=greeting,
            metadata={
                "user_id": user.id, 
                "greeting_type": command.greeting_type
            }
        )
    
    def handle_send_email(self, command: SendEmailCommand) -> CommandResult:
        """Handle the send email command.
        
        Args:
            command: The email command
            
        Returns:
            Command result
        """
        # Start a custom trace span
        span = self.obs_bus.start_trace(
            "email_operation", 
            {"operation": "send_email", "user_id": command.user_id}
        )
        
        # Get the user
        user = self.user_db.get_user(command.user_id)
        
        if not user:
            self.obs_bus.end_trace(span, "error")
            return CommandResult(
                command_id=command.id,
                success=False,
                error=f"User not found with ID: {command.user_id}"
            )
        
        # Random chance of simulated failure
        import random
        if random.random() < 0.3:  # 30% chance of failure
            self.obs_bus.end_trace(span, "error")
            return CommandResult(
                command_id=command.id,
                success=False,
                error="Email service temporarily unavailable"
            )
        
        # Send the email
        success = self.email_service.send_email(
            to_email=user.email,
            subject=command.subject,
            body=command.body
        )
        
        # End the trace
        status = "success" if success else "error"
        self.obs_bus.end_trace(span, status)
        
        # Record a metric
        self.obs_bus.metric(
            name="emails_sent",
            value=1,
            tags={"success": str(success)}
        )
        
        if success:
            return CommandResult(
                command_id=command.id,
                success=True,
                result={"sent": True, "to": user.email},
                metadata={"user_id": user.id, "email": user.email}
            )
        else:
            return CommandResult(
                command_id=command.id,
                success=False,
                error="Failed to send email"
            )
    
    def handle_user_registered(self, event: UserRegisteredEvent) -> None:
        """Handle user registered event by sending welcome email.
        
        Args:
            event: The user registered event
        """
        # Log this event
        self.obs_bus.log(
            LogLevel.INFO,
            f"User registered: {event.name} ({event.email})",
            {"user_id": event.user_id}
        )
        
        # Prepare welcome email command
        email_command = SendEmailCommand(
            user_id=event.user_id,
            subject="Welcome to LLMgine!",
            body=f"Hello {event.name},\n\nWelcome to LLMgine! We're excited to have you on board.\n\nBest regards,\nThe LLMgine Team"
        )
        
        # Schedule the command (executed via task to avoid blocking)
        asyncio.create_task(self.message_bus.execute(email_command))
    
    def handle_user_greeted(self, event: UserGreetedEvent) -> None:
        """Handle the user greeted event.
        
        Args:
            event: The user greeted event
        """
        self.obs_bus.log(
            LogLevel.INFO,
            f"User {event.user_id} was greeted with: {event.greeting_message}"
        )
    
    def handle_email_sent(self, event: EmailSentEvent) -> None:
        """Handle the email sent event.
        
        Args:
            event: The email sent event
        """
        self.obs_bus.log(
            LogLevel.INFO,
            f"Email sent to user {event.user_id} ({event.email}): {event.subject}"
        )
    
    def handle_trace_event(self, event: TraceEvent) -> None:
        """Handle trace events for demonstration.
        
        Args:
            event: The trace event
        """
        # This is mostly for demonstration purposes
        # Most of the trace handling is done by InMemoryTraceHandler
        pass
    
    async def register_user(self, name: str, email: str, 
                           preferences: Optional[Dict[str, Any]] = None) -> Optional[User]:
        """Register a new user by executing the registration command.
        
        Args:
            name: User name
            email: User email
            preferences: Optional user preferences
            
        Returns:
            The created user or None if failed
        """
        # Create the command
        command = UserRegistrationCommand(
            name=name,
            email=email,
            preferences=preferences or {}
        )
        
        # Execute the command
        result = await self.message_bus.execute(command)
        
        if result.success:
            # Get the created user
            user = result.result
            
            # Publish a user registered event
            await self.message_bus.publish(
                UserRegisteredEvent(
                    user_id=user.id,
                    name=user.name,
                    email=user.email
                )
            )
            
            return user
        else:
            error_msg = f"Failed to register user: {result.error}"
            self.obs_bus.log(LogLevel.ERROR, error_msg)
            return None
    
    async def greet_user(self, user_id: str, greeting_type: str = "standard") -> Optional[str]:
        """Greet a user by executing the greeting command.
        
        Args:
            user_id: The user ID to greet
            greeting_type: Type of greeting to use
            
        Returns:
            The greeting message or None if failed
        """
        # Create the command
        command = UserGreetingCommand(
            user_id=user_id,
            greeting_type=greeting_type
        )
        
        # Execute the command
        result = await self.message_bus.execute(command)
        
        if result.success:
            # Get the greeting
            greeting_message = result.result
            
            # Publish a user greeted event
            await self.message_bus.publish(
                UserGreetedEvent(
                    user_id=user_id,
                    greeting_message=greeting_message
                )
            )
            
            return greeting_message
        else:
            error_msg = f"Failed to greet user: {result.error}"
            self.obs_bus.log(LogLevel.ERROR, error_msg)
            return None
    
    async def send_email(self, user_id: str, subject: str, body: str) -> bool:
        """Send an email to a user.
        
        Args:
            user_id: The user ID to send to
            subject: Email subject
            body: Email body
            
        Returns:
            True if the email was sent
        """
        # Create the command
        command = SendEmailCommand(
            user_id=user_id,
            subject=subject,
            body=body
        )
        
        # Execute the command
        result = await self.message_bus.execute(command)
        
        if result.success:
            # Get the user to extract email
            user = self.user_db.get_user(user_id)
            
            # Publish an email sent event
            if user:
                await self.message_bus.publish(
                    EmailSentEvent(
                        user_id=user_id,
                        email=user.email,
                        subject=subject
                    )
                )
            
            return True
        else:
            error_msg = f"Failed to send email: {result.error}"
            self.obs_bus.log(LogLevel.ERROR, error_msg)
            return False


async def main():
    """Run the example application."""
    # Create and initialize our application
    app = ExampleApplication()
    await app.bootstrap()
    
    try:
        # Register some users
        alice = await app.register_user("Alice", "alice@example.com", {"theme": "dark"})
        bob = await app.register_user("Bob", "bob@example.com")
        charlie = await app.register_user("Charlie", "charlie@example.com")
        
        # Wait for event processing
        await asyncio.sleep(0.5)
        
        # Greet the users with different greeting types
        if alice:
            greeting1 = await app.greet_user(alice.id, "standard")
            print(f"\nStandard greeting for Alice: {greeting1}")
        
        if bob:
            greeting2 = await app.greet_user(bob.id, "formal")
            print(f"Formal greeting for Bob: {greeting2}")
        
        if charlie:
            greeting3 = await app.greet_user(charlie.id, "casual")
            print(f"Casual greeting for Charlie: {greeting3}")
        
        # Send some direct emails
        if alice:
            await app.send_email(
                alice.id, 
                "Your Account Summary", 
                "Here is your latest account summary..."
            )
        
        # Wait for all events to be processed
        await asyncio.sleep(1)
        
        # Print some metrics
        print("\n--- Metrics Summary ---")
        user_registrations = app.metrics_handler.get_metric("user_registrations")
        if user_registrations:
            print(f"User registrations: {user_registrations['value']}")
            
        emails_sent = app.metrics_handler.get_metric("emails_sent", {"success": "True"})
        if emails_sent:
            print(f"Successful emails sent: {emails_sent['value']}")
        
        # Print trace summary
        print("\n--- Recent Traces ---")
        recent_traces = app.trace_handler.get_recent_traces(5)
        for trace in recent_traces:
            print(f"Trace ID: {trace['trace_id'][:8]} ({len(trace['spans'])} spans)")
            for span_id, span in trace['spans'].items():
                # Only show parent spans (not children) for brevity
                if not span['parent_span_id']:
                    duration = span['duration_ms'] if span['duration_ms'] else 0
                    print(f"  - {span['name']} ({duration:.2f}ms) - {span['status']}")
        
        # Get service info
        print("\n--- Service Info ---")
        print(f"Registered users: {len(app.user_db.users)}")
        print(f"Emails sent: {len(app.email_service.sent_emails)}")
        
    finally:
        # Shutdown the application
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())