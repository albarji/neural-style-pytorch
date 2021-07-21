"""Main entrypoing for running style transfer as a python library

References:
    - Pytorch Neural Style tutorial: https://pytorch.org/tutorials/advanced/neural_style_tutorial.html
"""

from copy import deepcopy
import torch.optim as optim

from neuralstyle.styletransfernet import StyleTransferNet


def run_style_transfer(content_img, style_img, num_steps=300, style_weight=1000000, content_weight=1):
    """Run the style transfer"""
    # Initialize style network
    style_network = StyleTransferNet(content_img, style_img)
    # Initialize synthetic image with content image
    input_img = deepcopy(content_img)

    optimizer = optim.LBFGS([input_img.requires_grad_()])

    print('Optimizing...')
    run = [0]
    while run[0] <= num_steps:

        def closure():
            # correct the values of updated input image
            input_img.data.clamp_(0, 1)

            optimizer.zero_grad()
            style_network(input_img)
            style_score = 0
            content_score = 0

            for sl in style_network.style_losses:
                style_score += sl.loss
            for cl in style_network.content_losses:
                content_score += cl.loss

            style_score *= style_weight
            content_score *= content_weight

            loss = style_score + content_score
            loss.backward()

            run[0] += 1
            if run[0] % 50 == 0:
                print("run {}:".format(run))
                print('Style Loss : {:4f} Content Loss: {:4f}'.format(
                    style_score.item(), content_score.item()))
                print()

            return style_score + content_score

        optimizer.step(closure)

    # a last correction...
    input_img.data.clamp_(0, 1)

    return input_img


def format_input_images(content, style):
    """Scale and format input images for good performance of the Style Transfer method.
    
    This means:
        - Style image is rescaled to the same dimensions as the content image
        - Scale to VGG19 max dimension? 224x224
    """
    pass  # TODO