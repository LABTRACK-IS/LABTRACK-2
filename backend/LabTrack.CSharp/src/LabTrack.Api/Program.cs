using System.Security.Claims;
using System.Text.Encodings.Web;
using System.Text.Json;
using LabTrack.Api.Controllers;
using LabTrack.Api.Extensions;
using LabTrack.Api.Filters;
using LabTrack.Api.Health;
using LabTrack.Api.Hubs;
using LabTrack.Api.Middleware;
using LabTrack.Api.Services;
using LabTrack.Api.Workers;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.Extensions.Options;
using Npgsql;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpContextAccessor();
builder.Services.AddControllers(options =>
{
    options.Filters.Add<ValidateModelAttribute>();
});

builder.Services.AddEndpointsApiExplorer();

builder.Services.AddApplicationServices();

builder.Services.AddScoped<AuditContext>();

// API layer services (implement interfaces declared in Controllers)
builder.Services.AddScoped<LabTrack.Api.Controllers.IUserService, LabTrack.Api.Services.UserService>();
builder.Services.AddScoped<LabTrack.Api.Controllers.IAnalyticsService, LabTrack.Api.Services.AnalyticsService>();

builder.Services.AddLabTrackSwagger();

builder.Services.AddDistributedMemoryCache();

builder.Services.AddSignalR();

builder.Services.AddHttpClient<PythonAiHealthCheck>();

builder.Services.AddHealthChecks()
    .AddCheck<DatabaseHealthCheck>("database_check", tags: new[] { "db", "ready" })
    .AddCheck<PythonAiHealthCheck>("python_ai_check", tags: new[] { "ai", "ready" })
    .AddCheck<ReadinessHealthCheck>("readiness_check", tags: new[] { "readiness" });

builder.Services.AddHostedService<EmailDispatchWorker>();
builder.Services.AddHostedService<NotificationWorker>();
builder.Services.AddHostedService<PcSessionHeartbeatWorker>();

builder.Services.AddCors(options =>
{
    options.AddPolicy("LabTrackCorsPolicy", policy =>
    {
        policy.SetIsOriginAllowed(origin => true).AllowAnyHeader().AllowAnyMethod().AllowCredentials();
    });
});

builder.Services.AddDbContext<LabTrack.Infrastructure.Persistence.DbContext.LabTrackDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

builder.Services.AddScoped<
    LabTrack.Application.Interfaces.IUnitOfWork,
    LabTrack.Infrastructure.Persistence.Repositories.UnitOfWork>();

builder.Services.AddScoped<
    LabTrack.Application.Interfaces.IPasswordHasher,
    LabTrack.Infrastructure.Security.PasswordHasher>();

builder.Services.AddScoped<
    LabTrack.Application.Interfaces.IPythonAiClient,
    LabTrack.Infrastructure.Ai.PythonAiClient>();

builder.Services.AddHttpClient<LabTrack.Api.Services.PythonAiService>(client =>
{
    var baseUrl = builder.Configuration["PythonAi:BaseUrl"]
        ?? builder.Configuration["PythonAiUrl"]
        ?? builder.Configuration["PythonBaseUrl"]
        ?? "http://localhost:8000";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromSeconds(60);
});

builder.Services.AddScoped<
    LabTrack.Application.Interfaces.IQrGeneratorEngine,
    LabTrack.Infrastructure.Qr.QrGeneratorEngine>();

builder.Services.AddScoped<
    LabTrack.Application.Interfaces.IJwtTokenGenerator,
    LabTrack.Infrastructure.Security.JwtTokenGenerator>();

builder.Services.AddScoped<
    LabTrack.Application.Interfaces.IQrTokenService,
    LabTrack.Infrastructure.Qr.QrTokenService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.ILaboratoriesService,
    LabTrack.Api.Services.LaboratoriesService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.IAssetService,
    LabTrack.Api.Services.AssetService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.INotificationService,
    LabTrack.Api.Services.NotificationService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.IReservationService,
    LabTrack.Api.Services.ReservationService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.IProblemReportService,
    LabTrack.Api.Services.ProblemReportService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.IRepairTicketService,
    LabTrack.Api.Services.RepairTicketService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.IMaintenanceService,
    LabTrack.Api.Services.MaintenanceService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.IAuditLogService,
    LabTrack.Api.Services.AuditLogService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.ICommunicationService,
    LabTrack.Api.Services.CommunicationService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.IFinancialService,
    LabTrack.Api.Services.FinancialService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.INetworkService,
    LabTrack.Api.Services.NetworkService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.IQrService,
    LabTrack.Api.Services.QrService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.IReplacementService,
    LabTrack.Api.Services.ReplacementService>();

builder.Services.AddScoped<
    LabTrack.Api.Controllers.IPcUsageService,
    LabTrack.Api.Services.PcUsageService>();

builder.Services.AddAuthentication("Bearer")
    .AddScheme<AuthenticationSchemeOptions, LabTrackAuthHandler>("Bearer", null);

builder.Services.AddAuthorization();

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var startupLogger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();
    var connString = builder.Configuration.GetConnectionString("DefaultConnection");

    try
    {
        await using var conn = new NpgsqlConnection(connString);
        await conn.OpenAsync();

        startupLogger.LogInformation("==============================================");
        startupLogger.LogInformation("DATABASE CONNECTED SUCCESSFULLY");
        startupLogger.LogInformation("  Database : {Database}", conn.Database);
        startupLogger.LogInformation("  Host     : {Host}", conn.Host);
        startupLogger.LogInformation("  Port     : {Port}", conn.Port);
        startupLogger.LogInformation("  Server   : {Version}", conn.ServerVersion);
        startupLogger.LogInformation("==============================================");
    }
    catch (Exception ex)
    {
        startupLogger.LogError("==============================================");
        startupLogger.LogError("DATABASE CONNECTION FAILED");
        startupLogger.LogError("  Error: {Message}", ex.Message);
        startupLogger.LogError("==============================================");
    }
}

app.UseMiddleware<SecurityHeadersMiddleware>();
app.UseMiddleware<RequestIdMiddleware>();
app.UseMiddleware<ExceptionHandlingMiddleware>();

if (app.Environment.IsDevelopment() || app.Environment.IsStaging())
{
    app.UseLabTrackSwagger();
}

app.UseHttpsRedirection();
app.UseCors("LabTrackCorsPolicy");
app.UseRouting();

app.UseAuthentication();
app.UseMiddleware<JwtRoleMiddleware>();
app.UseMiddleware<AuditContextMiddleware>();
app.UseMiddleware<LabTrack.Api.Middleware.AuditLogMiddleware>();
app.UseAuthorization();

app.MapControllers();

app.MapHub<LabTrackHub>("/hubs/labtrack");
app.MapHub<AiChatHub>("/hubs/aichat");
app.MapHub<SessionHub>("/hubs/session");

app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = _ => false,
    ResponseWriter = WriteHealthResponseAsync
});

app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready") || check.Tags.Contains("readiness"),
    ResponseWriter = WriteHealthResponseAsync
});

app.Run();

static Task WriteHealthResponseAsync(HttpContext context, HealthReport report)
{
    context.Response.ContentType = "application/json";

    var response = new
    {
        status = report.Status.ToString(),
        totalDurationMilliseconds = report.TotalDuration.TotalMilliseconds,
        checks = report.Entries.Select(entry => new
        {
            name = entry.Key,
            status = entry.Value.Status.ToString(),
            description = entry.Value.Description,
            durationMilliseconds = entry.Value.Duration.TotalMilliseconds,
            exception = entry.Value.Exception?.Message
        })
    };

    var options = new JsonSerializerOptions
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true
    };

    return context.Response.WriteAsync(JsonSerializer.Serialize(response, options));
}

public class AuditContext
{
    public Guid? UserId { get; set; }
    public string? UserName { get; set; }
    public string? UserEmail { get; set; }
    public string? UserRole { get; set; }
    public string? IpAddress { get; set; }
    public string? UserAgent { get; set; }
    public string? CorrelationId { get; set; }
}

public class LabTrackAuthHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    public LabTrackAuthHandler(
        IOptionsMonitor<AuthenticationSchemeOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder)
        : base(options, logger, encoder)
    {
    }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, "00000000-0000-0000-0000-000000000001"),
            new Claim("sub", "00000000-0000-0000-0000-000000000001"),
            new Claim("userId", "00000000-0000-0000-0000-000000000001"),
            new Claim(ClaimTypes.Email, "technician@jrmsu.edu.ph"),
            new Claim(ClaimTypes.Name, "LabTrack Admin Technician"),
            new Claim(ClaimTypes.Role, "TECHNICIAN"),
            new Claim("role", "TECHNICIAN")
        };

        var identity = new ClaimsIdentity(claims, Scheme.Name);
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, Scheme.Name);

        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}