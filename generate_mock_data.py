"""
Generate mock data for admin user management testing.
"""
from app import create_app
from models import db, User, Account, AuditLog

def create_mock_data():
    app = create_app()
    with app.app_context():
        # Clear existing data (for fresh start)
        db.drop_all()
        db.create_all()

        # Create admin user
        admin = User(
            username="Andrew",
            email="drewbanda2@gmail.com",
            is_admin=True,
            is_active=True
        )
        admin.set_password("drew123")

        # Create regular users
        user1 = User(
            username="john_doe",
            email="john@gmail.com",
            is_admin=False,
            is_active=True
        )
        user1.set_password("john1")

        user2 = User(
            username="jane_smith",
            email="janesmith@gmail.com",
            is_admin=False,
            is_active=False  # Locked user
        )
        user2.set_password("jane2")

        user3 = User(
            username="bob_johnson",
            email="bob@example.com",
            is_admin=False,
            is_active=True
        )
        user3.set_password("password3")

        users = [admin, user1, user2, user3]
        db.session.add_all(users)
        db.session.commit()

        # Create accounts for each user
        accounts = [
            Account(user_id=admin.id, account_type="Savings", balance=5000.00),
            Account(user_id=admin.id, account_type="Checking", balance=1500.00),

            Account(user_id=user1.id, account_type="Savings", balance=2500.00),
            Account(user_id=user1.id, account_type="Checking", balance=500.00),

            Account(user_id=user2.id, account_type="Savings", balance=1000.00),

            Account(user_id=user3.id, account_type="Checking", balance=3000.00),
            Account(user_id=user3.id, account_type="Savings", balance=750.00),
        ]
        db.session.add_all(accounts)
        db.session.commit()

        # Create some audit log entries (simulating past actions)
        audit_entries = [
            AuditLog(
                admin_user_id=admin.id,
                target_user_id=user2.id,
                action="USER_LOCKED",
                details="Administrator locked the user account due to inactivity."
            ),
            AuditLog(
                admin_user_id=admin.id,
                target_user_id=user1.id,
                action="USER_UNLOCKED",
                details="Administrator unlocked the user account after verification."
            )
        ]
        db.session.add_all(audit_entries)
        db.session.commit()

        print("Mock data created successfully!")
        print(f"Created {len(users)} users")
        print(f"Created {len(accounts)} accounts")
        print(f"Created {len(audit_entries)} audit log entries")

if __name__ == "__main__":
    create_mock_data()
