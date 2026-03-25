# test_imports.py
try:
    print("Testing imports...")
    
    import flask
    print(f"✅ Flask: {flask.__version__}")
    
    import sklearn
    print(f"✅ scikit-learn: {sklearn.__version__}")
    
    import pandas as pd
    print(f"✅ pandas: {pd.__version__}")
    
    import numpy as np
    print(f"✅ numpy: {np.__version__}")
    
    from flask_mail import Mail
    print("✅ flask-mail")
    
    from apscheduler.schedulers.background import BackgroundScheduler
    print("✅ apscheduler")
    
    print("\n🎉 All packages installed successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nTry installing missing packages:")
    print("python -m pip install " + str(e).split("'")[1])