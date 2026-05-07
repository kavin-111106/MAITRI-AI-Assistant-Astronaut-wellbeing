import cv2
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# =========================
# SETTINGS
# =========================

MODEL_PATH = "model.pth"
IMG_SIZE = 224

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

# =========================
# CLASS NAMES
# =========================
# Change order if your dataset order is different

class_names = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "neutral",
    "sad",
    "surprise"
]

# =========================
# LOAD MODEL
# =========================

model = models.resnet18(pretrained=False)

num_ftrs = model.fc.in_features

model.fc = nn.Sequential(
    nn.Dropout(0.5),
    nn.Linear(num_ftrs, len(class_names))
)

checkpoint = torch.load(
    MODEL_PATH,
    map_location=device
)

# If saved as state_dict only
if isinstance(checkpoint, dict) and "model_state" in checkpoint:
    model.load_state_dict(checkpoint["model_state"])
else:
    model.load_state_dict(checkpoint)

model = model.to(device)

model.eval()

# =========================
# IMAGE TRANSFORM
# =========================

transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225]
    )
])

# =========================
# FACE DETECTOR
# =========================

face_cascade = cv2.CascadeClassifier(
    "haarcascade_frontalface_default.xml"
)

# =========================
# START WEBCAM
# =========================

webcam = cv2.VideoCapture(0)

if not webcam.isOpened():
    print("Could not open webcam")
    exit()

print("Webcam started... Press Q to quit")

# =========================
# WEBCAM LOOP
# =========================

while True:

    ret, frame = webcam.read()

    if not ret:
        break

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30,30)
    )

    for (x, y, w, h) in faces:

        # Crop face
        face = frame[y:y+h, x:x+w]

        # Convert BGR to RGB
        rgb = cv2.cvtColor(
            face,
            cv2.COLOR_BGR2RGB
        )

        # Convert to PIL Image
        pil_img = Image.fromarray(rgb)

        # Transform
        tensor = transform(pil_img)

        tensor = tensor.unsqueeze(0).to(device)

        # Prediction
        with torch.no_grad():

            outputs = model(tensor)

            probs = torch.softmax(
                outputs,
                dim=1
            )

            confidence, pred = torch.max(
                probs,
                dim=1
            )

            label = class_names[pred.item()]

            conf = confidence.item()

        # Draw rectangle
        cv2.rectangle(
            frame,
            (x, y),
            (x+w, y+h),
            (0,255,0),
            2
        )

        # Put label
        cv2.putText(
            frame,
            f"{label}: {conf*100:.1f}%",
            (x, y-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0,255,0),
            2
        )

    # Show frame
    cv2.imshow(
        "Emotion Detector",
        frame
    )

    # Quit on Q
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# =========================
# CLEANUP
# =========================

webcam.release()

cv2.destroyAllWindows()