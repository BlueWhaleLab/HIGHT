import torch
import torch.nn as nn
import re


class IdentityMap(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, x, *args, **kwargs):
        return x

    @property
    def config(self):
        return {"mm_projector_type": 'identity'}


class SimpleResBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.pre_norm = nn.LayerNorm(channels)

        self.proj = nn.Sequential(
            nn.Linear(channels, channels),
            nn.GELU(),
            nn.Linear(channels, channels)
        )
    def forward(self, x):
        x = self.pre_norm(x)
        return x + self.proj(x)


def build_xmodal_projector(config, delay_load=False, **kwargs):
    projector_type = getattr(config, 'mm_projector_type', 'linear')

    if projector_type == 'linear':
        return nn.Linear(config.mm_hidden_size, config.hidden_size)
    if projector_type == 'hlinear':
        modules = torch.nn.ModuleList()
        modules.append(nn.Linear(config.mm_hidden_size, config.hidden_size))
        modules.append(nn.Linear(config.mm_hidden_size, config.hidden_size))
        modules.append(nn.Linear(config.mm_hidden_size, config.hidden_size))
        return modules
    if projector_type == 'hlinear-mlp':
        modules = torch.nn.ModuleList()
        mlp_depth = 2
        modules0 = [nn.Linear(config.mm_hidden_size, config.hidden_size)]
        for _ in range(1, mlp_depth):
            modules0.append(nn.GELU())
            modules0.append(nn.Linear(config.hidden_size, config.hidden_size))
        modules.append(nn.Sequential(*modules0))
        modules1 = [nn.Linear(config.mm_hidden_size, config.hidden_size)]
        for _ in range(1, mlp_depth):
            modules1.append(nn.GELU())
            modules1.append(nn.Linear(config.hidden_size, config.hidden_size))
        modules.append(nn.Sequential(*modules1))
        modules2 = [nn.Linear(config.mm_hidden_size, config.hidden_size)]
        for _ in range(1, mlp_depth):
            modules2.append(nn.GELU())
            modules2.append(nn.Linear(config.hidden_size, config.hidden_size))
        modules.append(nn.Sequential(*modules2))
        return modules
    mlp_gelu_match = re.match(r'^mlp(\d+)x_gelu$', projector_type)
    if mlp_gelu_match:
        mlp_depth = int(mlp_gelu_match.group(1))
        modules = [nn.Linear(config.mm_hidden_size, config.hidden_size)]
        for _ in range(1, mlp_depth):
            modules.append(nn.GELU())
            modules.append(nn.Linear(config.hidden_size, config.hidden_size))
        return nn.Sequential(*modules)

    if projector_type == 'identity':
        return IdentityMap()

    raise ValueError(f'Unknown projector type: {projector_type}')
