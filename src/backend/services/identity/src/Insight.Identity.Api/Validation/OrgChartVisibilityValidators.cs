using FluentValidation;
using Insight.Identity.Api.Contracts;

namespace Insight.Identity.Api.Validation;

public sealed class CreateVisibilityCommandValidator : AbstractValidator<CreateVisibilityCommandModel>
{
    public CreateVisibilityCommandValidator()
    {
        RuleFor(x => x.ViewerPersonId)
            .NotEqual(Guid.Empty)
            .WithErrorCode("urn:insight:error:invalid_viewer_person_id")
            .WithMessage("viewer_person_id is required");

        RuleFor(x => x.Reason)
            .MaximumLength(500)
            .WithErrorCode("urn:insight:error:invalid_reason")
            .WithMessage("reason must be at most 500 characters");
    }
}

public sealed class CreateRoleCommandValidator : AbstractValidator<CreateRoleCommandModel>
{
    public CreateRoleCommandValidator()
    {
        RuleFor(x => x.Name)
            .NotEmpty()
            .WithErrorCode("urn:insight:error:invalid_role_name")
            .WithMessage("name is required")
            .MaximumLength(64)
            .WithErrorCode("urn:insight:error:invalid_role_name")
            .WithMessage("name must be at most 64 characters");
    }
}

public sealed class CreatePersonRoleCommandValidator : AbstractValidator<CreatePersonRoleCommandModel>
{
    public CreatePersonRoleCommandValidator()
    {
        RuleFor(x => x.PersonId)
            .NotEqual(Guid.Empty)
            .WithErrorCode("urn:insight:error:invalid_person_id")
            .WithMessage("person_id is required");

        RuleFor(x => x.RoleId)
            .NotEqual(Guid.Empty)
            .WithErrorCode("urn:insight:error:invalid_role_id")
            .WithMessage("role_id is required");

        RuleFor(x => x.Reason)
            .MaximumLength(500)
            .WithErrorCode("urn:insight:error:invalid_reason")
            .WithMessage("reason must be at most 500 characters");
    }
}

public sealed class RevokeReasonValidator : AbstractValidator<RevokeReasonModel>
{
    public RevokeReasonValidator()
    {
        RuleFor(x => x.Reason)
            .MaximumLength(500)
            .WithErrorCode("urn:insight:error:invalid_reason")
            .WithMessage("reason must be at most 500 characters");
    }
}
