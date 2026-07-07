from django.contrib.auth.base_user import BaseUserManager

# user custom manager
class UserManager(BaseUserManager):

    # create user method for creating a user with email and phone number
    def create_user(self, email, phone_number=None, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email) # normalize the email address by lowercasing the domain part of it
        user = self.model(email=email, phone_number=phone_number, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # if no password is provided, set an unusable password
        
        user.save(using=self._db)
        return user
    
    # create superuser method for creating a superuser with email and phone number
    def create_superuser(self, email, phone_number=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_email_verified', True)

        # only set is_phone_verified to True if phone_number is provided
        if phone_number:
            extra_fields.setdefault('is_phone_verified', True)

        # super user must be a staff and superuser
        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, phone_number, password, **extra_fields)
