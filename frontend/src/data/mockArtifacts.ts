import { Artifact } from "@/components/ArtifactCard";

export const mockArtifacts: Artifact[] = [
  {
    id: "1",
    name: "ResNet-50 Image Classifier",
    type: "model",
    description: "Deep residual network trained on ImageNet with 50 layers. Achieves 76.1% top-1 accuracy on validation set.",
    uploadDate: "2025-10-20T10:30:00",
    netScore: 0.89,
    size: "98 MB"
  },
  {
    id: "2",
    name: "CIFAR-10 Training Dataset",
    type: "dataset",
    description: "60,000 32x32 color images in 10 classes, with 6,000 images per class. Preprocessed and augmented for training.",
    uploadDate: "2025-10-18T14:22:00",
    netScore: 0.95,
    size: "163 MB"
  },
  {
    id: "3",
    name: "Data Preprocessing Pipeline",
    type: "code",
    description: "Complete preprocessing pipeline with normalization, augmentation, and batch generation utilities for image datasets.",
    uploadDate: "2025-10-15T09:15:00",
    netScore: 0.82,
    size: "2.4 MB"
  },
  {
    id: "4",
    name: "BERT-Base Text Classifier",
    type: "model",
    description: "Fine-tuned BERT model for sentiment analysis on movie reviews. Achieves 94.2% accuracy on test set.",
    uploadDate: "2025-10-12T16:45:00",
    netScore: 0.91,
    size: "438 MB"
  },
  {
    id: "5",
    name: "Customer Reviews Dataset",
    type: "dataset",
    description: "Labeled dataset of 50,000 customer reviews with sentiment annotations. Balanced distribution across 5 categories.",
    uploadDate: "2025-10-10T11:20:00",
    netScore: 0.88,
    size: "78 MB"
  },
  {
    id: "6",
    name: "Training Loop Implementation",
    type: "code",
    description: "Modular training loop with early stopping, learning rate scheduling, and checkpoint management.",
    uploadDate: "2025-10-08T13:55:00",
    netScore: 0.86,
    size: "1.2 MB"
  },
  {
    id: "7",
    name: "YOLOv5 Object Detector",
    type: "model",
    description: "Real-time object detection model optimized for edge devices. Detects 80 common object classes with high precision.",
    uploadDate: "2025-10-05T08:30:00",
    netScore: 0.87,
    size: "28 MB"
  },
  {
    id: "8",
    name: "Urban Scenes Dataset",
    type: "dataset",
    description: "10,000 annotated images of urban environments with bounding boxes for pedestrians, vehicles, and road signs.",
    uploadDate: "2025-10-02T15:10:00",
    netScore: 0.93,
    size: "1.2 GB"
  }
];
