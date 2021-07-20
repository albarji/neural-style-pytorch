"""Implementation of a style transfer network

References:
    - Gatys et al. - A Neural Algorithm of Artistic Style - https://arxiv.org/abs/1508.06576
    - Pytorch Neural Style tutorial: https://pytorch.org/tutorials/advanced/neural_style_tutorial.html
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models


class StyleTransferNet(torch.nn.Module):
    """Neural network that implements the style transfer algorithm of Gatys"""
    vgg19_normalization_mean = torch.tensor([0.485, 0.456, 0.406])
    vgg19_normalization_std = torch.tensor([0.229, 0.224, 0.225])
    content_layers_default = ['conv_4']
    style_layers_default = ['conv_1', 'conv_2', 'conv_3', 'conv_4', 'conv_5']

    def __init__(self, content_img, style_img):
        super(StyleTransferNet, self).__init__()
        # Initialize VGG19 reference architecture
        cnn = models.vgg19(pretrained=True).features.eval()

        # Start with image normalization layer
        normalization = Normalization(self.vgg19_normalization_mean, self.vgg19_normalization_std)
        self.model = nn.Sequential(normalization)

        # Add VGG19 layers, with added losses
        self.content_losses = []
        self.style_losses = []
        i = 0  # increment every time we see a conv
        for layer in cnn.children():
            if isinstance(layer, nn.Conv2d):
                i += 1
                name = 'conv_{}'.format(i)
            elif isinstance(layer, nn.ReLU):
                name = 'relu_{}'.format(i)
                # The in-place version doesn't play very nicely with the ContentLoss
                # and StyleLoss we insert below. So we replace with out-of-place
                # ones here.
                layer = nn.ReLU(inplace=False)
            elif isinstance(layer, nn.MaxPool2d):
                name = 'pool_{}'.format(i)
            elif isinstance(layer, nn.BatchNorm2d):
                name = 'bn_{}'.format(i)
            else:
                raise RuntimeError('Unrecognized layer: {}'.format(layer.__class__.__name__))

            self.model.add_module(name, layer)

            if name in self.content_layers_default:
                # add content loss:
                target = self.model(content_img).detach()
                content_loss = ContentLoss(target)
                self.model.add_module("content_loss_{}".format(i), content_loss)
                self.content_losses.append(content_loss)

            if name in self.style_layers_default:
                # add style loss:
                target_feature = self.model(style_img).detach()
                style_loss = StyleLoss(target_feature)
                self.model.add_module("style_loss_{}".format(i), style_loss)
                self.style_losses.append(style_loss)

        # now we trim off the layers after the last content and style losses
        for i in range(len(self.model) - 1, -1, -1):
            if isinstance(self.model[i], ContentLoss) or isinstance(self.model[i], StyleLoss):
                break

        self.model = self.model[:(i + 1)]

    def forward(self, x):
        return self.model(x)


class ContentLoss(nn.Module):
    """Style transfer content loss: penalizes differences between a target image and generated image activations"""
    def __init__(self, target):
        super(ContentLoss, self).__init__()
        self.target = target.detach()  # Do not compute gradients for target image

    def forward(self, input):
        self.loss = F.mse_loss(input, self.target)
        return input


def gram_matrix(input):
    """Computes the Gram matrix of a single image after a convolution layer"""
    a, b, c, d = input.size()  # a=batch size(=1)
                               # b=number of feature maps (convolution channels)
                               # (c,d)=dimensions of a f. map (N=c*d)
    features = input.view(a * b, c * d)  # resise F_XL into \hat F_XL

    G = torch.mm(features, features.t())  # compute the gram product

    # we 'normalize' the values of the gram matrix
    # by dividing by the number of element in each feature maps.
    return G.div(a * b * c * d)


class StyleLoss(nn.Module):
    """Style transfer style loss: penalizes differences between target image and generated image Gram matrices (activation correlations)"""
    def __init__(self, target):
        super(StyleLoss, self).__init__()
        self.target = gram_matrix(target).detach()

    def forward(self, input):
        G = gram_matrix(input)
        self.loss = F.mse_loss(G, self.target)
        return input


class Normalization(nn.Module):
    """Layer that normalizes an image using given mean and standard deviation statistics"""
    def __init__(self, mean, std):
        super(Normalization, self).__init__()
        # .view the mean and std to make them [C x 1 x 1] so that they can
        # directly work with image Tensor of shape [B x C x H x W].
        # B is batch size. C is number of channels. H is height and W is width.
        self.mean = torch.tensor(mean).view(-1, 1, 1)
        self.std = torch.tensor(std).view(-1, 1, 1)

    def forward(self, img):
        # normalize img
        return (img - self.mean) / self.std
