import os
import utils
import config
import traceback
from luna import LunaExcepion

from keras.applications.vgg16 import VGG16
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential, Model
from keras.layers import Input, Activation, Dropout, Flatten, Dense
from keras import optimizers
import numpy as np

classes = ['Tulip', 'Snowdrop', 'LilyValley', 'Bluebell', 'Crocus',
           'Iris', 'Tigerlily', 'Daffodil', 'Fritillary', 'Sunflower',
           'Daisy', 'ColtsFoot', 'Dandelion', 'Cowslip', 'Buttercup',
           'Windflower', 'Pansy']
nb_classes = len(classes)
nb_train_samples = 1190
nb_val_samples = 170
nb_epoch = 50


if __name__ == '__main__':
    try:
        utils.lock()

        if not os.path.exists(config.result_dir):
            os.mkdir(config.result_dir)

        # VGG16モデルと学習済み重みをロード
        # Fully-connected層（FC）はいらないのでinclude_top=False）
        input_tensor = Input(shape=(config.img_height, config.img_width, 3))
        vgg16_model = VGG16(include_top=False, weights='imagenet', input_tensor=input_tensor)
        # FC層を構築
        # Flattenへの入力指定はバッチ数を除く
        top_model = Sequential()
        top_model.add(Flatten(input_shape=vgg16_model.output_shape[1:]))
        top_model.add(Dense(256, activation='relu'))
        top_model.add(Dropout(0.5))
        top_model.add(Dense(1, activation='softmax'))
        # 二つのモデルを結合する
        model = Model(input=vgg16_model.input, output=top_model(vgg16_model.output))
        # 最後のconv層の直前までの層をfreeze
        for layer in model.layers[:15]:
            layer.trainable = False

        model.summary()

        model.compile(
            loss='categorical_crossentropy',
            optimizer=optimizers.SGD(lr=1e-4, momentum=0.9),
            metrics=['accuracy']
        )

        # 訓練データを生成するジェネレータを作成
        train_datagen = ImageDataGenerator(
            preprocessing_function=utils.preprocess_images,
            shear_range=0.2,
            zoom_range=0.2,
            horizontal_flip=True
        )
        train_generator = train_datagen.flow_from_directory(
            config.train_dir,
            target_size=(150, 150),
            batch_size=32,
            color_mode='rgb',
            classes=classes,
            class_mode='categorical',
            shuffle=True
        )

        # 検証データを生成するジェネレータを作成
        test_datagen = ImageDataGenerator(preprocessing_function=utils.preprocess_images)
        validation_generator = test_datagen.flow_from_directory(
            config.validation_dir,
            target_size=(150, 150),
            batch_size=32,
            color_mode='rgb',
            classes=classes,
            class_mode='categorical',
            shuffle=True
        )

        print(train_generator.class_indices)

        # 訓練
        history = model.fit_generator(
            train_generator,
            samples_per_epoch=nb_train_samples,
            nb_epoch=nb_epoch,
            validation_data=validation_generator,
            nb_val_samples=nb_val_samples
        )
        utils.plot_history(history)

        # 結果を保存
        model.save(os.path.join(config.result_dir, 'finetuning_model.h5'))
        model.save_weights(os.path.join(config.result_dir, 'finetuning_weights.h5'))
        utils.save_history(history, os.path.join(config.result_dir, 'finetuning_history.txt'))

    except (KeyboardInterrupt, SystemExit):
        utils.unlock()
        utils.error(config.syserr)
    except LunaExcepion as e:
        utils.error(e.value)
    except Exception as e:
        utils.error(config.syserr)
        print(e)
        print(traceback.format_exc())
    utils.unlock()

