import tensorflow as tf
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
import helpers
import ssd

args = helpers.handle_args()
if args.handle_gpu:
    helpers.handle_gpu_compatibility()

train_batch_size = 2
val_batch_size = 8
epochs = 50
load_weights = False
ssd_type = "ssd300"
hyper_params = helpers.get_hyper_params(ssd_type)

VOC_train_data, VOC_info = helpers.get_VOC_data("train")
VOC_val_data, _ = helpers.get_VOC_data("validation")
VOC_train_total_items = helpers.get_total_item_size(VOC_info, "train")
VOC_val_total_items = helpers.get_total_item_size(VOC_info, "validation")
labels = helpers.get_labels(VOC_info)
# We add 1 class for background
hyper_params["total_labels"] = len(labels) + 1
img_size = helpers.SSD[ssd_type]["img_size"]

VOC_train_data = VOC_train_data.map(lambda x : helpers.preprocessing(x, img_size, img_size))
VOC_val_data = VOC_val_data.map(lambda x : helpers.preprocessing(x, img_size, img_size))

padded_shapes, padding_values = helpers.get_padded_batch_params()
VOC_train_data = VOC_train_data.padded_batch(train_batch_size, padded_shapes=padded_shapes, padding_values=padding_values)
VOC_val_data = VOC_val_data.padded_batch(val_batch_size, padded_shapes=padded_shapes, padding_values=padding_values)
#
ssd_model = ssd.get_model(hyper_params)
ssd_model.compile(optimizer=tf.optimizers.Adam(learning_rate=1e-5),
                loss=[None] * len(ssd_model.output))
ssd_model_path = helpers.get_model_path(ssd_type)
if load_weights:
    ssd_model.load_weights(ssd_model_path)

# We calculate prior boxes for one time and use it for all operations because of the all images are the same sizes
prior_boxes = ssd.generate_prior_boxes(hyper_params["img_size"], hyper_params["feature_map_shapes"], hyper_params["aspect_ratios"])
ssd_train_feed = ssd.generator(VOC_train_data, prior_boxes, hyper_params, preprocess_input)
ssd_val_feed = ssd.generator(VOC_val_data, prior_boxes, hyper_params, preprocess_input)

custom_callback = helpers.CustomCallback(ssd_model_path, monitor="val_loss", patience=5)

step_size_train = VOC_train_total_items // train_batch_size
step_size_val = VOC_val_total_items // val_batch_size
ssd_model.fit(ssd_train_feed,
                steps_per_epoch=step_size_train,
                validation_data=ssd_val_feed,
                validation_steps=step_size_val,
                epochs=epochs,
                callbacks=[custom_callback])